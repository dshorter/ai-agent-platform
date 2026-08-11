#!/usr/bin/env python3
"""Build the lead routing desk — gate ①'s first usable surface.

Step 3 of the pipeline (dispose the Wire Editor's shortlist) is the
operator's, and as of 2026-08-03 it had never once been exercised: the
only shortlist ever produced lived in a gitignored YAML plus a claude.ai
artifact that 404'd on the operator's phone, and applying a verdict meant
hand-typing a lead_mark line per lead. The tooling assumed appetite the
delivery path had already killed. This desk is the draft-review pattern
pointed at routing: one card per proposal — the pitch, the Wire Editor's
verdict, the chief shadow's — thumb claim or spike, paste the block.

Untouched cards are holds: leaving a lead alone IS a legal disposition
(it stays `new` for the next pass), so the desk never nags for coverage.
Every verdict pasted here is a HUMAN one — the apply block never emits
--agent — and each one is the concordance metric's first real data
(see lead_mark: agent-applied marks are excluded from scoring).

The page never writes anything. Same contract as every desk: read-only
surface, verdicts travel by copy-paste, mutation stays in lead_mark.

    .venv/bin/python tools/wire_review.py            # latest proposals artifact
    .venv/bin/python tools/wire_review.py --proposals pipelines/wire_editor/state/proposals/2026-07-18.yaml
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

# One visual system across the desks: reuse the draft desk's CSS and its
# redaction-aware escaper (pitches are transcript-derived, so they go
# through the same detector the drafts do).
_spec = importlib.util.spec_from_file_location(
    "draft_review", Path(__file__).resolve().parent / "draft_review.py"
)
_dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dr)
esc, CSS = _dr.esc, _dr.CSS

STATE_DIR = Path(os.environ.get("WIRE_EDITOR_STATE_DIR", _REPO / "pipelines" / "wire_editor" / "state"))
LEADS_PATH = Path(os.environ.get("SCOUT_LEADS_PATH", _REPO / "pipelines" / "scout" / "state" / "leads.yaml"))
OUT_PATH = Path(os.environ.get("WIRE_REVIEW_OUT", STATE_DIR / "review" / "index.html"))

# Attention order, not artifact order: claims are the cards that cost money
# downstream (each claim becomes a Writer run), spikes are the bulk, holds sit
# between. Within a group the artifact's order is preserved.
VERDICT_ORDER = {"claim": 0, "hold": 1, "spike": 2}


def parse_artifact(path: Path) -> dict:
    """Parse the _artifact() emission (pipelines/wire_editor/run.py) — the
    same hand-rolled flat-YAML dialect the rest of the shop reads."""
    header, date = "", ""
    clusters: list[dict] = []
    proposals: list[dict] = []
    cur: dict | None = None
    section = None
    unq = lambda v: v[1:-1] if len(v) >= 2 and v[0] == v[-1] == '"' else v
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("# ") and not header:
            header = raw[2:]
            continue
        if raw.startswith("date: "):
            date = raw[6:].strip()
            continue
        if raw == "clusters:":
            section = "clusters"
            continue
        if raw == "proposals:":
            section = "proposals"
            cur = None
            continue
        if section == "clusters":
            m = re.match(r'  - theme: (.+)$', raw)
            if m:
                clusters.append({"theme": unq(m.group(1).strip()), "ids": []})
            m = re.match(r'    ids: \[(.*)\]$', raw)
            if m and clusters:
                clusters[-1]["ids"] = [i.strip() for i in m.group(1).split(",") if i.strip()]
        elif section == "proposals":
            m = re.match(r'  - id: (\S+)$', raw)
            if m:
                cur = {"id": m.group(1), "flags": []}
                proposals.append(cur)
                continue
            m = re.match(r'    (\w+): (.+)$', raw)
            if m and cur is not None:
                key, val = m.group(1), m.group(2).strip()
                if key == "flags":
                    cur["flags"] = [f.strip() for f in val.strip("[]").split(",") if f.strip()]
                else:
                    cur[key] = unq(val)
    return {"header": header, "date": date, "clusters": clusters, "proposals": proposals}


def merge_artifacts(paths: list[Path]) -> dict:
    """All artifacts, merged: a backlog now pages across several files
    (run.py --limit/--skip-proposed, forced by the 64k output ceiling), so
    the desk shows the union. Where a lead appears in more than one, the
    later artifact's verdict wins — a re-proposed hold carries the wire's
    latest thinking, not its first."""
    merged: dict[str, dict] = {}
    clusters: list[dict] = []
    header = date = ""
    # NOT plain alphabetical: run.py names the day's first artifact
    # YYYY-MM-DD.yaml and later ones YYYY-MM-DD-HHMM.yaml, and "-1357"
    # sorts before ".yaml" — so the plain (earliest) file would win
    # precedence over its same-day successors. Key the bare date as 0000.
    def when(p: Path) -> tuple[str, str]:
        stem = p.stem
        return (stem[:10], stem[11:] or "0000")
    for p in sorted(paths, key=when):
        art = parse_artifact(p)
        header, date = art["header"], art["date"]
        clusters.extend(art["clusters"])
        for prop in art["proposals"]:
            if prop["id"] in merged:
                merged[prop["id"]].update(prop)
            else:
                merged[prop["id"]] = prop
    return {"header": header, "date": date, "clusters": clusters,
            "proposals": list(merged.values())}


def split_by_status(proposals: list[dict], leads: dict[str, dict]) -> tuple[list[dict], int]:
    """Cards vs already-disposed. A proposal whose lead is no longer `new`
    already has its verdict — counting it as awaiting would be the same bug
    the draft desk had. A lead MISSING from the ledger is shown (fail open),
    flagged rather than hidden."""
    pending, decided = [], 0
    for p in proposals:
        lead = leads.get(p["id"])
        if lead is None:
            p["_missing"] = True
            pending.append(p)
        elif lead.get("status", "new") == "new":
            pending.append(p)
        else:
            decided += 1
    return pending, decided


EXTRA_CSS = """
/* Routing-desk additions on top of the draft desk's system. */
.v{display:inline-block;font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;
font-weight:650;padding:.16rem .5rem;border-radius:99px}
.v-claim{background:var(--upbg);color:var(--up)}
.v-spike{background:var(--downbg);color:var(--down)}
.v-hold{background:var(--line);color:var(--dim)}
.leadid{font-family:var(--mono);font-size:.72rem;color:var(--dim);overflow-wrap:anywhere}
.pitch{font-family:var(--serif);font-size:1.02rem;line-height:1.6;margin:.5rem 0 .8rem}
.whynow{font-size:.85rem;color:var(--dim);margin:0 0 .8rem}
.whynow b{color:var(--fg);font-weight:620}
.desk{border-top:1px solid var(--line);padding-top:.7rem;font-size:.85rem;
display:grid;gap:.45rem}
.desk .row{display:flex;gap:.55rem;align-items:baseline;flex-wrap:wrap}
.desk .who{font:600 .68rem/1.6 var(--sans);text-transform:uppercase;
letter-spacing:.07em;color:var(--dim);flex:none;width:3.4rem}
.desk .why{color:var(--dim)}
.differ .desk .row.chief .why{color:var(--warnc)}
.differ-badge{font-size:.68rem;color:var(--warnc);border:1px solid currentColor;
padding:.1rem .45rem;border-radius:99px}
.cluster{font-size:.72rem;color:var(--dim);margin-top:.15rem}
.missing{font-size:.78rem;color:var(--warnc);margin:.4rem 0 0}
.card.claim{border-color:var(--up);box-shadow:inset 3px 0 0 var(--up)}
.card.spike{border-color:var(--down);box-shadow:inset 3px 0 0 var(--down);opacity:.55}
.card.claim .tu{background:var(--upbg);border-color:var(--up)}
.card.spike .td{background:var(--downbg);border-color:var(--down)}
"""

JS = """
const KEY = 'wire-review-v1';
const FKEY = 'wire-review-filter';
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch(e) { state = {}; }
let filter = localStorage.getItem(FKEY) || 'all';

const cards = [...document.querySelectorAll('.card')];
const navs = [...document.querySelectorAll('.navitem')];
if (!navs.some(n => n.dataset.f === filter)) filter = 'all';

function visible(c){
  if (filter === 'all') return true;
  if (filter === 'differ') return c.dataset.differ === '1';
  return c.dataset.wire === filter;
}

function render(){
  let claims = 0, spikes = 0;
  const per = {claim:{t:0,d:0}, hold:{t:0,d:0}, spike:{t:0,d:0}, differ:{t:0,d:0}};
  for (const c of cards){
    const v = state[c.dataset.lead];
    c.classList.toggle('claim', v === 'claim');
    c.classList.toggle('spike', v === 'spike');
    c.hidden = !visible(c);
    if (v === 'claim') claims++; else if (v === 'spike') spikes++;
    const w = c.dataset.wire;
    if (per[w]) { per[w].t++; if (v) per[w].d++; }
    if (c.dataset.differ === '1') { per.differ.t++; if (v) per.differ.d++; }
  }
  for (const n of navs){
    const f = n.dataset.f;
    n.classList.toggle('on', f === filter);
    n.setAttribute('aria-pressed', f === filter);
    const s = f === 'all' ? {t: cards.length, d: claims + spikes} : (per[f] || {t:0,d:0});
    n.querySelector('.n').innerHTML = (s.d ? '<span class="d">' + s.d + '</span>/' : '') + s.t;
  }
  document.getElementById('tally').textContent =
    claims + ' claim \\u00b7 ' + spikes + ' spike \\u00b7 ' +
    (cards.length - claims - spikes) + ' left as hold';

  // The apply block. Untouched cards emit NOTHING — a hold is a lead left at
  // `new` for the next pass, not a verdict to record. And every line is plain
  // `--by editor`, never agent-attributed: this block is the human's pen,
  // which is the entire point of the desk.
  const up = cards.filter(c => state[c.dataset.lead] === 'claim');
  const down = cards.filter(c => state[c.dataset.lead] === 'spike');
  const L = [];
  if (up.length){
    L.push('# Claim ' + up.length + ' \\u2014 from /opt/ai-agent-platform');
    up.forEach(c => L.push('.venv/bin/python -m pipelines.scout.lead_mark ' + c.dataset.lead + ' --to claimed --by editor'));
  }
  if (down.length){
    if (L.length) L.push('');
    L.push('# Spike ' + down.length + ' \\u2014 from /opt/ai-agent-platform');
    down.forEach(c => L.push('.venv/bin/python -m pipelines.scout.lead_mark ' + c.dataset.lead + ' --to spiked --by editor'));
  }
  if (L.length){
    L.push('');
    L.push('# Then refresh this page \\u2014 your verdicts just made it stale:');
    L.push('.venv/bin/python tools/wire_review.py');
  }
  if (up.length){
    L.push('');
    L.push('# Later, hand each claim to the Writer (one model run apiece):');
    up.forEach(c => L.push('#   .venv/bin/python -m pipelines.writer ' + c.dataset.lead));
  }
  document.getElementById('cmds').textContent =
    L.length ? L.join('\\n') : 'Thumb a lead to build the apply block. Untouched = hold.';
}

document.addEventListener('click', e => {
  const b = e.target.closest('.thumbs button');
  if (!b) return;
  const id = b.closest('.card').dataset.lead;
  state[id] = state[id] === b.dataset.v ? undefined : b.dataset.v;
  if (!state[id]) delete state[id];
  localStorage.setItem(KEY, JSON.stringify(state));
  render();
});

document.querySelector('.rail').addEventListener('click', e => {
  const n = e.target.closest('.navitem');
  if (!n) return;
  filter = n.dataset.f;
  localStorage.setItem(FKEY, filter);
  render();
  const smooth = !matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.scrollTo({top: 0, behavior: smooth ? 'smooth' : 'auto'});
});

document.getElementById('reset').addEventListener('click', () => {
  if (!confirm('Clear every verdict on this page?')) return;
  state = {}; localStorage.removeItem(KEY); render();
});

document.getElementById('copy').addEventListener('click', async () => {
  const t = document.getElementById('cmds').textContent;
  try { await navigator.clipboard.writeText(t); }
  catch(e) {
    const r = document.createRange(); r.selectNode(document.getElementById('cmds'));
    getSelection().removeAllRanges(); getSelection().addRange(r);
  }
  const b = document.getElementById('copy'); const o = b.textContent;
  b.textContent = 'copied'; setTimeout(() => b.textContent = o, 1200);
});

render();
"""


def render_card(p: dict, lead: dict, cluster: str | None, i: int) -> str:
    wire = p.get("wire", "hold")
    reg = p.get("register", "note")
    chief_stance = p.get("chief", "silent")
    chief_v = p.get("chief_verdict", "")
    differ = chief_stance == "differ"
    flags = "".join(
        f'<span class="flag">{html.escape(f)}</span>' for f in p.get("flags", [])
    )
    differ_badge = '<span class="differ-badge">chief differs</span>' if differ else ""
    missing = (
        '<p class="missing">Not in the ledger &mdash; shown so nothing vanishes silently; '
        "lead_mark will refuse it.</p>" if p.get("_missing") else ""
    )
    chief_row = (
        f'<div class="row chief"><span class="who">chief</span>'
        f'<span class="v v-{html.escape(chief_v or wire)}">{html.escape(chief_v or wire)}</span>'
        f'<span class="why">{esc(p.get("chief_reason", "")) or html.escape(chief_stance)}</span></div>'
        if chief_stance != "silent" else
        '<div class="row chief"><span class="who">chief</span><span class="why">silent</span></div>'
    )
    return f"""
<article class="card{' differ' if differ else ''}" data-lead="{html.escape(p['id'])}" data-wire="{html.escape(wire)}" data-differ="{'1' if differ else '0'}">
  <header class="chead">
    <div class="crumbs"><span class="reg reg-{html.escape(reg)}">{html.escape(reg)}</span>
      <span class="num">#{i}</span>{differ_badge}{flags}</div>
    <div class="thumbs">
      <button class="tu" data-v="claim" title="Claim it — worth pursuing">&#128077;</button>
      <button class="td" data-v="spike" title="Spike it — not worth telling">&#128078;</button>
    </div>
  </header>
  <div class="leadid">{html.escape(p['id'])}</div>
  <p class="pitch">{esc(lead.get('pitch', ''))}</p>
  {f'<p class="whynow"><b>Why now.</b> {esc(lead.get("why_now", ""))}</p>' if lead.get('why_now') else ''}
  <div class="desk">
    <div class="row"><span class="who">wire</span>
      <span class="v v-{html.escape(wire)}">{html.escape(wire)}</span>
      <span class="why">{esc(p.get('reason', ''))}</span></div>
    {chief_row}
  </div>
  {f'<div class="cluster">cluster: {html.escape(cluster)}</div>' if cluster else ''}
  {missing}
</article>"""


def build(art: dict, leads: dict[str, dict]) -> tuple[str, dict]:
    pending, decided = split_by_status(art["proposals"], leads)
    pending.sort(key=lambda p: VERDICT_ORDER.get(p.get("wire", "hold"), 1))
    by_cluster = {i: c["theme"] for c in art["clusters"] for i in c["ids"]}

    counts = {"claim": 0, "hold": 0, "spike": 0, "differ": 0}
    cards = []
    for i, p in enumerate(pending, 1):
        counts[p.get("wire", "hold")] = counts.get(p.get("wire", "hold"), 0) + 1
        if p.get("chief") == "differ":
            counts["differ"] += 1
        cards.append(render_card(p, leads.get(p["id"], {}), by_cluster.get(p["id"]), i))

    rail_rows = "".join(
        f'<button class="navitem" data-f="{f}" aria-pressed="false">'
        f'<span>{label}</span><span class="n"></span></button>'
        for f, label in (
            ("claim", "Wire says claim"), ("hold", "Wire says hold"),
            ("spike", "Wire says spike"), ("differ", "Chief differs"),
        )
    )
    rail = (
        '<nav class="rail" aria-label="Filter by wire verdict"><h2>Wire verdict</h2>'
        '<button class="navitem" data-f="all" aria-pressed="true">'
        '<span>Everything</span><span class="n"></span></button>'
        f"{rail_rows}"
        '<div class="railfoot">Filtering changes the view only — the apply block '
        "always covers every verdict. Untouched cards are holds.</div></nav>"
    )

    body = "".join(cards) if cards else (
        '<div class="empty"><p><b>Nothing awaiting routing.</b></p>'
        "<p>Every proposal in the latest artifact already has a verdict. "
        "Run a fresh pass when the queue has grown:</p>"
        "<p><code>.venv/bin/python -m pipelines.wire_editor --pass</code></p></div>"
    )

    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Lead routing desk</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}{EXTRA_CSS}</style>
</head><body><div class="shell">
{rail}
<div class="wrap">
<header class="top">
  <h1>Lead routing desk</h1>
  <p class="sub">Gate &#9312;. Thumb up to claim, thumb down to spike, leave alone to hold.
  The wire and chief columns are suggestions &mdash; your call is the ground truth
  the concordance metric scores them against.</p>
  <div class="counts">
    <div><b>{len(pending)}</b><span>awaiting routing</span></div>
    <div><b>{counts['claim']}</b><span>wire says claim</span></div>
    <div><b>{counts['spike']}</b><span>wire says spike</span></div>
    <div><b>{counts['differ']}</b><span>chief differs</span></div>
    <div><b>{decided}</b><span>already disposed</span></div>
  </div>
  <p class="sub" style="margin-top:.6rem">{html.escape(art['header'])}</p>
</header>
{body}
<div class="apply">
  <div class="bar">
    <h3>Apply block</h3>
    <button id="copy" class="primary">copy</button>
    <button id="reset">clear</button>
    <span class="tally" id="tally"></span>
  </div>
  <pre id="cmds"></pre>
</div>
</div></div><script>{JS}</script></body></html>
"""
    return page, {"pending": len(pending), "decided": decided, **counts}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proposals", help="review one artifact only (default: merge every artifact)")
    ap.add_argument("--leads-path", default=str(LEADS_PATH))
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args(argv)

    if args.proposals:
        paths = [Path(args.proposals)]
    else:
        pdir = STATE_DIR / "proposals"
        paths = sorted(pdir.glob("*.yaml")) if pdir.is_dir() else []
    if not paths or not all(p.is_file() for p in paths):
        print("no proposals artifact found — run: .venv/bin/python -m pipelines.wire_editor --pass",
              file=sys.stderr)
        return 1

    art = merge_artifacts(paths)
    leads = {l["id"]: l for l in load_leads(Path(args.leads_path))}
    page, stats = build(art, leads)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    names = ", ".join(p.name for p in paths)
    print(
        f"built {out}  ({stats['pending']} lead(s) awaiting routing from {names}; "
        f"{stats['decided']} already disposed)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
