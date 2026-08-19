#!/usr/bin/env python3
"""Build the leads archive — the whole ledger, and what became of each lead.

The routing desk (wire_review.py) shows what still needs a verdict. This is
the other half: every lead the Scout has ever filed, in one scrollable
column, with the Wire Editor's recommendation and the ledger's own
provenance stamps side by side. Two questions it exists to answer at a
glance — what did the wire say about this, and what did we actually do.

Those are not the same question, and on 2026-08-19 they had diverged badly:
the Wire Editor had verdicts on 257 leads (120 claim, 127 spike) and the
ledger still read `new` for 470 of 477, because step 3 — the operator's
disposition — is the one step no timer performs. A surface that shows the
two columns next to each other makes that gap visible instead of arithmetic.

A lead the wire has never seen is shown as such, never as a hold: "no
recommendation yet" and "recommended you leave it alone" are different
facts, and collapsing them would overstate how much triage has happened.

Read-only, like every desk. It hands back ids; `lead_mark` is still the only
verb that writes to the ledger, and the routing desk is still where verdicts
get collected. Browsing is not deciding, and this page deliberately cannot
decide.

    .venv/bin/python tools/leads_archive.py          # build + print the path
    .venv/bin/python tools/leads_archive.py --out /tmp/leads.html
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import os
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from pipelines.writer.assignment import load_leads  # noqa: E402


def _sibling(name: str):
    """Load a sibling tool as a module. The desks share their visual system
    and their parsers by importing each other rather than by copy — one
    stylesheet, one redaction escaper, one artifact parser across the shop."""
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parent / f"{name}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_dr = _sibling("draft_review")
_wr = _sibling("wire_review")
esc, CSS = _dr.esc, _dr.CSS
merge_artifacts = _wr.merge_artifacts

LEADS_PATH = Path(os.environ.get("SCOUT_LEADS_PATH", _REPO / "pipelines" / "scout" / "state" / "leads.yaml"))
PROPOSALS_DIR = Path(os.environ.get("WIRE_EDITOR_STATE_DIR", _REPO / "pipelines" / "wire_editor" / "state")) / "proposals"
OUT_PATH = Path(os.environ.get("LEADS_ARCHIVE_OUT", _REPO / "pipelines" / "scout" / "state" / "archive" / "index.html"))

# The ledger's lifecycle, in order. Drives both the rail and the timeline —
# a stamp is `<state>_on`, so the vocabulary and the field names are the
# same list read two ways (lead_mark owns the transitions themselves).
LIFECYCLE = ["claimed", "drafted", "approved", "published", "rejected", "spiked"]
STATUSES = ["new"] + LIFECYCLE

# Wire verdicts, plus the fourth state the artifacts cannot express: a lead
# filed after the last wire pass has no recommendation at all.
WIRE_STATES = [
    ("claim", "Wire says claim"),
    ("spike", "Wire says spike"),
    ("hold", "Wire says hold"),
    ("unseen", "Not yet triaged"),
]

_STAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s*(?:\((.*)\))?$")

EXTRA_CSS = """
/* A ledger reads as rows, not cards: 477 of them, scanned for the one you
   want. The pitch lives inside a disclosure row so the column stays scannable
   and the page still carries everything without a second request. */
.wrap.arch{max-width:none}
.tools{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;margin:1rem 0 .4rem}
.tools input{flex:1;min-width:11rem;font:inherit;font-size:.88rem;padding:.5rem .75rem;
border:1px solid var(--line);border-radius:9px;background:var(--card);color:var(--fg)}
.tools input:focus-visible{outline:2px solid var(--acc);outline-offset:1px;border-color:var(--acc)}
.tools .shown{font-size:.8rem;color:var(--dim);font-variant-numeric:tabular-nums;flex:none}
.rowlist{margin-top:.8rem;border:1px solid var(--line);border-radius:12px;
background:var(--card);overflow:hidden}
/* Reset what the draft desk's generic `details` rule assumes — there a
   disclosure is a rare aside with air around it, here it IS the row, and
   inherited margin/padding/top-border would double every separator. */
.lead{margin:0;padding:0;border-top:none;font-size:1rem;
border-bottom:1px solid var(--line)}
.lead:last-child{border-bottom:none}
.lead[hidden]{display:none}
/* Accent is reserved for things that navigate. The whole row is the
   affordance, so hover carries it and the slug stays body-coloured —
   477 lines of blue monospace reads as a link farm, not a ledger. */
.lead>summary{display:grid;grid-template-columns:5.4rem 1fr auto;gap:.5rem .8rem;
align-items:baseline;padding:.7rem .9rem;cursor:pointer;list-style:none;
color:var(--fg);font-size:1rem}
.lead>summary::-webkit-details-marker{display:none}
.lead>summary:hover{background:var(--bg)}
.lead[open]>summary{background:var(--bg);border-bottom:1px solid var(--line)}
.lead .when{font-variant-numeric:tabular-nums;font-size:.78rem;color:var(--dim);white-space:nowrap}
.lead .slug{font-family:var(--mono);font-size:.79rem;line-height:1.45;overflow-wrap:anywhere;
min-width:0}
.lead .marks{display:flex;gap:.35rem;align-items:center;flex:none;flex-wrap:wrap;
justify-content:flex-end}
/* Two verdict columns, deliberately styled apart: the wire's is a filled
   pill (a recommendation, softly stated), the ledger's is outlined (what is
   actually true). Same glance, different weight. */
.w{font-size:.64rem;text-transform:uppercase;letter-spacing:.06em;font-weight:650;
padding:.14rem .45rem;border-radius:99px;white-space:nowrap}
.w-claim{background:var(--upbg);color:var(--up)}
.w-spike{background:var(--downbg);color:var(--down)}
.w-hold{background:var(--line);color:var(--dim)}
.w-unseen{background:transparent;color:var(--dim);border:1px dotted var(--line)}
.st{font-size:.64rem;text-transform:uppercase;letter-spacing:.06em;font-weight:650;
padding:.13rem .45rem;border-radius:99px;white-space:nowrap;border:1px solid currentColor}
.st-new{color:var(--dim)}
.st-claimed,.st-drafted{color:var(--acc)}
.st-approved,.st-published{color:var(--up)}
.st-rejected,.st-spiked{color:var(--down)}
.differ-dot{color:var(--warnc);font-size:.8rem;flex:none}
.differ-dot.soft{opacity:.45}
.dnote{color:var(--warnc);font-weight:650}
.dnote.soft{color:var(--dim);font-weight:600}
.detail{padding:.95rem 1.1rem 1.2rem;display:grid;gap:.85rem}
.detail .pitch{font-family:var(--serif);font-size:1rem;line-height:1.6;margin:0}
.detail .whynow{margin:0;font-size:.88rem;color:var(--dim);line-height:1.55}
.detail .whynow b{color:var(--fg);font-weight:640}
.panel{border:1px solid var(--line);border-radius:9px;padding:.6rem .8rem;background:var(--bg)}
.panel h4{margin:0 0 .45rem;font-size:.66rem;text-transform:uppercase;
letter-spacing:.09em;color:var(--dim);font-weight:650}
.vrow{display:grid;grid-template-columns:3.6rem auto 1fr;gap:.5rem;align-items:baseline;
padding:.25rem 0;font-size:.85rem;line-height:1.5}
.vrow .who{font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;color:var(--dim);
font-weight:650}
/* A pill is a label, not a bar: without this it stretches to fill its
   grid cell once the row collapses to two columns on a phone. */
.vrow .w{justify-self:start}
.vrow .why{color:var(--dim)}
.tl{list-style:none;margin:0;padding:0;font-size:.83rem}
.tl li{display:grid;grid-template-columns:5.4rem 5.5rem 1fr;gap:.5rem;padding:.22rem 0;
line-height:1.5}
.tl .d{font-variant-numeric:tabular-nums;color:var(--dim)}
.tl .s{font-weight:640}
.tl .by{color:var(--dim)}
.tl .by .ag{color:var(--warnc)}
.meta{display:flex;gap:.5rem 1.1rem;flex-wrap:wrap;font-size:.76rem;color:var(--dim);
align-items:center}
.meta code{font-family:var(--mono);font-size:.95em;background:var(--bg);
border:1px solid var(--line);border-radius:5px;padding:.1rem .35rem;overflow-wrap:anywhere}
.meta button{font:inherit;font-size:.74rem;font-family:var(--mono);background:transparent;
border:1px dashed var(--line);border-radius:6px;padding:.14rem .45rem;color:var(--fg);cursor:copy}
.meta button:hover{border-style:solid;border-color:var(--acc)}
.srcs{margin:0;padding-left:1.1rem;font-size:.79rem;color:var(--dim);line-height:1.55}
.noneleft{padding:2.4rem 1rem;text-align:center;color:var(--dim);font-size:.9rem}
.foot{margin-top:1.6rem;padding-top:.9rem;border-top:1px solid var(--line);
color:var(--dim);font-size:.78rem;line-height:1.65}
.foot code{font-family:var(--mono);background:var(--card);border:1px solid var(--line);
border-radius:5px;padding:.1rem .35rem}
@media(max-width:860px){
  .lead>summary{grid-template-columns:1fr auto;gap:.3rem .6rem;padding:.65rem .75rem}
  .lead .when{grid-row:2;font-size:.72rem}
  .lead .slug{grid-column:1;font-size:.76rem}
  .lead .marks{grid-row:1/3;grid-column:2;flex-direction:column;align-items:flex-end;
    justify-content:center}
  .vrow{grid-template-columns:3.2rem auto;gap:.35rem}
  .vrow .why{grid-column:1/-1}
  .tl li{grid-template-columns:5.2rem 1fr;gap:.3rem}
  .tl .by{grid-column:1/-1}
}
"""

JS = """
const KEY = 'leads-archive-v1';
let f = {wire:'all', status:'all', q:''};
try { Object.assign(f, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch(e) {}

const rows  = [...document.querySelectorAll('.lead')];
const navs  = [...document.querySelectorAll('.navitem')];
const box   = document.getElementById('q');
const shown = document.getElementById('shown');

// Search covers the text a person actually remembers a lead by — its slug and
// its pitch — not the metadata, which the rail already filters better than
// free text can.
rows.forEach(r => { r.dataset.hay = (r.dataset.slug + ' ' + r.textContent).toLowerCase(); });

function apply(){
  const q = f.q.trim().toLowerCase();
  let n = 0;
  for (const r of rows){
    const ok = (f.wire === 'all' || r.dataset.wire === f.wire)
            && (f.status === 'all' || r.dataset.status === f.status)
            && (!q || r.dataset.hay.includes(q));
    r.hidden = !ok;
    if (ok) n++;
  }
  shown.textContent = n + (n === 1 ? ' lead' : ' leads');
  document.getElementById('noneleft').hidden = n > 0;
  for (const b of navs){
    const on = f[b.dataset.dim] === b.dataset.v;
    b.classList.toggle('on', on);
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
  }
  localStorage.setItem(KEY, JSON.stringify(f));
}

navs.forEach(b => b.addEventListener('click', () => {
  // Clicking the active facet clears it — otherwise the only way back to
  // "everything" is to remember which row means all.
  f[b.dataset.dim] = (f[b.dataset.dim] === b.dataset.v) ? 'all' : b.dataset.v;
  apply();
}));

box.value = f.q;
box.addEventListener('input', () => { f.q = box.value; apply(); });

// Copy the id, because the next step is always pasting it into lead_mark.
document.addEventListener('click', async ev => {
  const b = ev.target.closest('button.cp');
  if (!b) return;
  try {
    await navigator.clipboard.writeText(b.dataset.id);
    const was = b.textContent; b.textContent = 'copied';
    setTimeout(() => { b.textContent = was; }, 1100);
  } catch(e) {
    const r = document.createRange(); r.selectNode(b.previousElementSibling || b);
    getSelection().removeAllRanges(); getSelection().addRange(r);
  }
});

apply();
"""


def parse_stamp(val: str) -> tuple[str, str, bool]:
    """`2026-07-30 (editor, agent)` -> (date, actor, was_agent).

    The `agent` marker is the whole reason the stamp has a parenthetical at
    all (lead_mark: concordance scores human verdicts only), so it survives
    into the timeline rather than being flattened into the actor string."""
    m = _STAMP_RE.match(val.strip())
    if not m:
        return val.strip(), "", False
    date, who = m.group(1), (m.group(2) or "").strip()
    parts = [p.strip() for p in who.split(",") if p.strip()]
    agent = "agent" in parts
    actor = ", ".join(p for p in parts if p != "agent")
    return date, actor, agent


def timeline(lead: dict) -> list[tuple[str, str, str, bool]]:
    """Every provenance stamp on a lead, oldest first."""
    out = []
    for state in LIFECYCLE:
        raw = lead.get(f"{state}_on")
        if raw:
            date, actor, agent = parse_stamp(raw)
            out.append((date, state, actor, agent))
    out.sort(key=lambda r: r[0])
    return out


def render_row(lead: dict, prop: dict | None, cluster: str | None) -> str:
    lid = lead["id"]
    status = lead.get("status", "new")
    reg = lead.get("register", "note")
    wire = (prop or {}).get("wire") or "unseen"
    # A "differ" from the chief shadow is two different events wearing one
    # word: 7 of the 8 on record carry the SAME verdict as the wire and
    # disagree only about emphasis (priority, slot rationing), while one
    # actually calls a different disposition. Only the second is a routing
    # disagreement; showing both as bare "differs" next to two identical
    # pills reads as a rendering fault, which is how it was first mistaken.
    differ = (prop or {}).get("chief") == "differ"
    differ_verdict = differ and (prop or {}).get("chief_verdict") != (prop or {}).get("wire")

    marks = (
        f'<span class="w w-{html.escape(wire)}">{html.escape("no wire pass" if wire == "unseen" else wire)}</span>'
        f'<span class="st st-{html.escape(status)}">{html.escape(status)}</span>'
    )
    if differ:
        title = ("the chief shadow called a different verdict" if differ_verdict
                 else "the chief shadow agreed on the verdict but differed on emphasis")
        marks = (f'<span class="differ-dot{"" if differ_verdict else " soft"}" '
                 f'title="{title}">&#9679;</span>') + marks

    # The two verdict columns. The wire's reasoning is worth reading even
    # when it agreed with itself; the chief only earns a line when it spoke.
    if prop:
        chief_stance = prop.get("chief", "silent")
        chief_v = prop.get("chief_verdict") or prop.get("wire", "")
        rows = (
            f'<div class="vrow"><span class="who">wire</span>'
            f'<span class="w w-{html.escape(prop.get("wire", "hold"))}">{html.escape(prop.get("wire", "hold"))}</span>'
            f'<span class="why">{esc(prop.get("reason", ""))}</span></div>'
        )
        if chief_stance != "silent":
            note = ("" if chief_stance != "differ" else
                    ' <b class="dnote">differs on the verdict.</b> ' if differ_verdict else
                    ' <b class="dnote soft">same call, different emphasis.</b> ')
            rows += (
                f'<div class="vrow"><span class="who">chief</span>'
                f'<span class="w w-{html.escape(chief_v)}">{html.escape(chief_v)}</span>'
                f'<span class="why">{note}{esc(prop.get("chief_reason", "")) or html.escape(chief_stance)}</span></div>'
            )
        else:
            rows += '<div class="vrow"><span class="who">chief</span><span></span><span class="why">silent</span></div>'
        if cluster:
            rows += f'<div class="vrow"><span class="who">cluster</span><span></span><span class="why">{esc(cluster)}</span></div>'
        wire_panel = f'<div class="panel"><h4>Wire Editor</h4>{rows}</div>'
    else:
        wire_panel = (
            '<div class="panel"><h4>Wire Editor</h4><p class="whynow">Filed after the '
            'last wire pass &mdash; no recommendation exists for this lead yet.</p></div>'
        )

    tl = timeline(lead)
    if tl:
        items = "".join(
            f'<li><span class="d">{html.escape(d)}</span><span class="s">{html.escape(s)}</span>'
            f'<span class="by">{html.escape(actor or "—")}'
            f'{" <span class=\"ag\">(agent)</span>" if agent else ""}</span></li>'
            for d, s, actor, agent in tl
        )
        tl_panel = f'<div class="panel"><h4>Ledger timeline</h4><ul class="tl">{items}</ul></div>'
    else:
        tl_panel = (
            '<div class="panel"><h4>Ledger timeline</h4><p class="whynow">No verdict has '
            'ever been applied &mdash; the lead is exactly as the Scout filed it.</p></div>'
        )

    srcs = "".join(f"<li>{esc(s)}</li>" for s in lead.get("sources", []))
    why = lead.get("why_now", "")

    return f"""
<details class="lead" data-wire="{html.escape(wire)}" data-status="{html.escape(status)}"
         data-slug="{html.escape(lid)}">
  <summary>
    <span class="when">{html.escape(lead.get('filed', ''))}</span>
    <span class="slug">{html.escape(lid)}</span>
    <span class="marks">{marks}</span>
  </summary>
  <div class="detail">
    <p class="pitch">{esc(lead.get('pitch', ''))}</p>
    {f'<p class="whynow"><b>Why now.</b> {esc(why)}</p>' if why else ''}
    {wire_panel}
    {tl_panel}
    {f'<div class="panel"><h4>Sources</h4><ul class="srcs">{srcs}</ul></div>' if srcs else ''}
    <div class="meta">
      <span class="reg reg-{html.escape(reg)}">{html.escape(reg)}</span>
      <code>{html.escape(lid)}</code>
      <button class="cp" data-id="{html.escape(lid)}">copy id</button>
      <span>filed by {html.escape(lead.get('model', 'unknown'))}</span>
      <span>redaction: {html.escape(lead.get('redaction', 'n/a'))}</span>
    </div>
  </div>
</details>"""


def build(leads: list[dict], props: dict[str, dict], clusters: dict[str, str]) -> tuple[str, dict]:
    # Newest first: browsing a ledger means starting from what just landed.
    leads = sorted(leads, key=lambda l: (l.get("filed", ""), l["id"]), reverse=True)

    wire_counts = {k: 0 for k, _ in WIRE_STATES}
    status_counts = {s: 0 for s in STATUSES}
    differ = 0
    rows = []
    for lead in leads:
        p = props.get(lead["id"])
        w = (p or {}).get("wire") or "unseen"
        wire_counts[w] = wire_counts.get(w, 0) + 1
        st = lead.get("status", "new")
        status_counts[st] = status_counts.get(st, 0) + 1
        if p and p.get("chief") == "differ":
            differ += 1
        rows.append(render_row(lead, p, clusters.get(lead["id"])))

    def facet(dim: str, v: str, label: str, n: int) -> str:
        return (f'<button class="navitem" data-dim="{dim}" data-v="{v}" aria-pressed="false">'
                f'<span>{html.escape(label)}</span><span class="n">{n}</span></button>')

    rail = (
        '<nav class="rail" aria-label="Filter the ledger">'
        '<h2>Wire verdict</h2>'
        + "".join(facet("wire", k, label, wire_counts.get(k, 0)) for k, label in WIRE_STATES)
        + '<h2 style="margin-top:1.1rem">Ledger status</h2>'
        + "".join(facet("status", s, s, status_counts.get(s, 0))
                  for s in STATUSES if status_counts.get(s, 0))
        + '<div class="railfoot">Click an active facet to clear it. Filters stack: '
          'wire verdict AND ledger status AND the search box.</div></nav>'
    )

    # The headline number is the gap itself — how many leads carry a wire
    # recommendation that the ledger has never acted on. It is the reason
    # this page exists, so it does not hide inside a filter.
    awaiting = sum(1 for l in leads
                   if l.get("status") == "new" and (props.get(l["id"]) or {}).get("wire") in ("claim", "spike"))

    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<meta name="referrer" content="no-referrer">
<title>Leads archive</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}{EXTRA_CSS}</style>
</head><body><div class="shell">
{rail}
<div class="wrap arch">
<header class="top">
  <h1>Leads archive</h1>
  <p class="sub">Every lead the Scout has filed, what the Wire Editor recommended,
  and what the ledger actually records. Read-only &mdash; verdicts are applied with
  <code>lead_mark</code>, and collected on the routing desk.</p>
  <div class="counts">
    <div><b>{len(leads)}</b><span>leads filed</span></div>
    <div><b>{wire_counts.get('claim', 0)}</b><span>wire: claim</span></div>
    <div><b>{wire_counts.get('spike', 0)}</b><span>wire: spike</span></div>
    <div><b>{wire_counts.get('unseen', 0)}</b><span>never triaged</span></div>
    <div><b>{awaiting}</b><span>triaged, still undisposed</span></div>
    <div><b>{differ}</b><span>chief differed</span></div>
  </div>
  <div class="tools">
    <input id="q" type="search" placeholder="Search slugs and pitches&hellip;"
           aria-label="Search leads" autocomplete="off">
    <span class="shown" id="shown"></span>
  </div>
</header>
<div class="rowlist">{"".join(rows)}
</div>
<p class="noneleft" id="noneleft" hidden>Nothing matches those filters.</p>
<p class="foot">Browsing is not deciding: nothing on this page writes. To dispose of a
lead, run <code>.venv/bin/python -m pipelines.scout.lead_mark &lt;id&gt; --to &lt;state&gt; --by editor</code>
on the box &mdash; and pass <code>--agent</code> if an agent, not you, made the call, because
concordance scores human verdicts only. The routing desk collects verdicts in batches.</p>
</div></div><script>{JS}</script></body></html>
"""
    return page, {"leads": len(leads), "awaiting": awaiting, "unseen": wire_counts.get("unseen", 0),
                  "differ": differ}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--leads-path", default=str(LEADS_PATH))
    ap.add_argument("--proposals-dir", default=str(PROPOSALS_DIR))
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args(argv)

    leads = load_leads(Path(args.leads_path))
    if not leads:
        print(f"no leads in {args.leads_path}", file=sys.stderr)
        return 1

    pdir = Path(args.proposals_dir)
    paths = sorted(pdir.glob("*.yaml")) if pdir.is_dir() else []
    if paths:
        art = merge_artifacts(paths)
        props = {p["id"]: p for p in art["proposals"]}
        clusters = {i: c["theme"] for c in art["clusters"] for i in c["ids"]}
    else:
        # No wire pass has ever run. Every lead reads `unseen`, which is the
        # honest rendering — not an error.
        props, clusters = {}, {}

    page, stats = build(leads, props, clusters)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"built {out}  ({stats['leads']} leads; {stats['awaiting']} triaged but undisposed; "
          f"{stats['unseen']} never triaged; {stats['differ']} chief disagreements)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
