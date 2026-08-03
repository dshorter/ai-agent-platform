#!/usr/bin/env python3
"""Build the draft review desk — one scrollable page, thumbs up or down.

Reads the Writer's gitignored drafts plus uzelhub-web's notes.json, and
emits ONE self-contained HTML file: every draft as a card in reading order,
rendered close to how it will publish, with a thumb on each.

Thumbs up does not publish. It queues — and the page shows you the drip
schedule that results, so approving six notes visibly lays them out across
three weeks instead of pretending they all ship Tuesday. That is the whole
point of reviewing in a batch (PUBLISHING.md: 1-2 URLs a week, never bulk).

The page never writes anything. It collects your verdicts and hands back an
apply block to run — the operator's pen, same contract as the Wire Editor's
proposals artifact.

    .venv/bin/python tools/draft_review.py                 # build + print the path
    .venv/bin/python tools/draft_review.py --open          # also print a file:// URL
    .venv/bin/python tools/draft_review.py --slots tue,fri # change the weekly slots
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "tools"))

from promote_draft import load_drafts, load_notes  # noqa: E402
from pipelines.writer.assignment import load_leads  # noqa: E402
from pipelines.writer.redaction import scan, scan_note  # noqa: E402

DRAFTS_DIR = Path(os.environ.get("WRITER_DRAFTS_DIR", _REPO / "pipelines" / "writer" / "state" / "drafts"))
NOTES_PATH = Path(os.environ.get("UZELHUB_NOTES_PATH", "/opt/uzelhub-web/marketing/data/notes.json"))
OUT_PATH = Path(os.environ.get("REVIEW_OUT", _REPO / "pipelines" / "writer" / "state" / "review" / "index.html"))
LEADS_PATH = Path(os.environ.get("SCOUT_LEADS_PATH", _REPO / "pipelines" / "scout" / "state" / "leads.yaml"))

# A verdict already given. The desk exists to COLLECT a verdict, so a lead that
# has one has no business on it. `drafted` is the only status that still needs
# one; a missing lead is shown rather than hidden, so nothing vanishes silently.
DECIDED = {"approved", "rejected", "published", "spiked"}

MIN_GAP_DAYS = 3  # mirrors release.js — the cadence guard is the doctrine
WEEKDAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


def drip_slots(notes: list[dict], slots: list[int], count: int, today: dt.date) -> list[dt.date]:
    """The next `count` publishable dates.

    Two rules stacked: the weekly slots give the cadence (1-2 a week, on
    predictable days), and MIN_GAP_DAYS re-checks every candidate against
    the one before it so the schedule can never violate release.js's guard.
    """
    published = sorted(n["published"] for n in notes if n.get("published"))
    last = dt.date.fromisoformat(published[-1]) if published else None
    out: list[dt.date] = []
    day = today
    horizon = today + dt.timedelta(days=365)
    while len(out) < count and day <= horizon:
        if day.weekday() in slots:
            prev = out[-1] if out else last
            if prev is None or (day - prev).days >= MIN_GAP_DAYS:
                out.append(day)
        day += dt.timedelta(days=1)
    return out


def esc(text: str) -> str:
    """Escape, and strike through anything the redaction detector flags.

    Split on the RAW string's offsets and escape each piece separately —
    escaping first would shift every offset by the length of each entity it
    expanded, and the marks would land in the wrong place.

    Struck-through rather than blacked out: the reviewer needs to READ what was
    caught in order to judge whether it should really be withheld. A censor's
    block hides the very thing the decision depends on.
    """
    findings = scan(text)
    if not findings:
        return html.escape(text)
    out, cursor = [], 0
    for f in findings:
        out.append(html.escape(text[cursor:f.start]))
        out.append(
            f'<s class="red" tabindex="0" title="{html.escape(f.kind)} — {html.escape(f.why)}">'
            f'{html.escape(f.text)}</s><sup class="redk">{html.escape(f.kind)}</sup>'
        )
        cursor = f.end
    out.append(html.escape(text[cursor:]))
    return "".join(out)


def render_body(body: list) -> str:
    """A section body item is a paragraph, or a receipt list. NEWSROOM's
    shape amendment: enumerable receipts render as lists so scannability
    never costs the receipts."""
    parts = []
    for item in body:
        if isinstance(item, str):
            parts.append(f"<p>{esc(item)}</p>")
        elif isinstance(item, dict) and "list" in item:
            lis = "".join(f"<li>{esc(str(x))}</li>" for x in item["list"])
            parts.append(f"<ul>{lis}</ul>")
        elif isinstance(item, dict) and "numbered" in item:
            lis = "".join(f"<li>{esc(str(x))}</li>" for x in item["numbered"])
            parts.append(f"<ol>{lis}</ol>")
    return "".join(parts)


def render_card(d: dict, i: int) -> str:
    note, lead = d["note"], d.get("lead", {})
    slug = note["slug"]
    reg = lead.get("register", "note")
    meta = note.get("metaDescription", "")
    meta_len = len(meta)
    # Google truncates around 155-160 chars; flag the ones that will clip.
    # No meta description at all is a different state from a bad one — show
    # nothing rather than a bogus "0 chars" warning.
    meta_cls = "ok" if 80 <= meta_len <= 160 else "warn"
    seo_block = (
        f'<div class="seo"><span class="lbl">meta description</span>'
        f'<span class="len {meta_cls}">{meta_len} chars</span>'
        f"<p>{esc(meta)}</p></div>" if meta else ""
    )

    bullets = "".join(f"<li>{esc(str(b))}</li>" for b in note.get("bullets", []))
    sections = "".join(
        f"<h3>{esc(s.get('h', ''))}</h3>{render_body(s.get('body', []))}"
        for s in note.get("sections", [])
    )
    receipts = "".join(f"<li>{html.escape(str(s))}</li>" for s in d.get("sources_cited", []))
    redaction = lead.get("redaction", "")
    flag = '<span class="flag">redaction: required</span>' if redaction == "required" else ""

    # The detector's verdict for this card. `redaction: required` is a constant
    # on every lead and says only that the gate applies; THIS says whether
    # anything actually tripped it. A count of zero is a real, useful signal —
    # it is the difference between "unscanned" and "scanned and clean".
    hits = scan_note(note)
    if hits:
        rows = "".join(
            f'<li><span class="rk">{html.escape(f.kind)}</span>'
            f'<code>{html.escape(f.text)}</code>'
            f'<span class="rw">{html.escape(f.why)}</span>'
            f'<span class="rp">{html.escape(path)}</span></li>'
            for path, f in hits
        )
        redpanel = (
            f'<details class="redpanel" open><summary>'
            f'{len(hits)} to verify before this can publish</summary>'
            f'<p class="rnote">Struck through in the copy below. Confirm each one really '
            f'should be withheld &mdash; then promote with <code>--redact</code>, which '
            f'replaces it with a visible [redacted] marker. Promote refuses without it.</p>'
            f'<ul>{rows}</ul></details>'
        )
    else:
        redpanel = '<p class="redclean">Scanned for credentials and PII &mdash; nothing found.</p>'


    return f"""
<article class="card" data-slug="{html.escape(slug)}" data-lead="{html.escape(lead.get('id',''))}" data-reg="{html.escape(reg)}" data-title="{html.escape(note.get('title',''))}">
  <header class="chead">
    <div class="crumbs"><span class="reg reg-{html.escape(reg)}">{html.escape(reg)}</span>
      <span class="num">#{i}</span>{flag}</div>
    <div class="thumbs">
      <button class="tu" data-v="up" title="Queue it">&#128077;</button>
      <button class="td" data-v="down" title="Spike it">&#128078;</button>
    </div>
  </header>
  <div class="kicker">{html.escape(note.get('kicker','Field note'))}</div>
  <h2>{esc(note.get('title',''))}</h2>
  <p class="tagline">{esc(note.get('tagline',''))}</p>
  {redpanel}
  {seo_block}
  {f'<ul class="bullets">{bullets}</ul>' if bullets else ''}
  <div class="body">{sections}</div>
  {f'<details class="receipts"><summary>Receipts &mdash; {len(d.get("sources_cited",[]))} sources cited</summary><ul>{receipts}</ul></details>' if receipts else ''}
  <details class="prov"><summary>Lead &amp; provenance</summary>
    <p><b>Pitch.</b> {html.escape(lead.get('pitch',''))}</p>
    <p><b>Why now.</b> {html.escape(lead.get('why_now',''))}</p>
    <p class="stamp">{html.escape(note.get('copyDraft',''))}</p>
  </details>
  <div class="slot" data-slot></div>
</article>"""


CSS = """
/* Two type roles that mean something: serif is the copy under review,
   sans is the desk around it. You can tell at a glance which is which. */
:root{
  --bg:#f6f6f4;--card:#fff;--fg:#17181c;--dim:#64666e;--line:#e4e4e1;
  --acc:#2f5d8a;--up:#1c7a52;--upbg:#e7f3ec;--down:#a8433c;--downbg:#faebe9;--warnc:#8a6100;
  --serif:Charter,"Iowan Old Style","Source Serif Pro",Georgia,serif;
  --sans:ui-sans-serif,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,monospace;
}
@media(prefers-color-scheme:dark){:root{
  --bg:#14151a;--card:#1b1d23;--fg:#e6e6e2;--dim:#93959d;--line:#2a2d35;
  --acc:#82b4e2;--up:#57c795;--upbg:#152e26;--down:#e4867e;--downbg:#321e1d;--warnc:#d3a24e;}}
:root[data-theme="dark"]{
  --bg:#14151a;--card:#1b1d23;--fg:#e6e6e2;--dim:#93959d;--line:#2a2d35;
  --acc:#82b4e2;--up:#57c795;--upbg:#152e26;--down:#e4867e;--downbg:#321e1d;--warnc:#d3a24e;}
:root[data-theme="light"]{
  --bg:#f6f6f4;--card:#fff;--fg:#17181c;--dim:#64666e;--line:#e4e4e1;
  --acc:#2f5d8a;--up:#1c7a52;--upbg:#e7f3ec;--down:#a8433c;--downbg:#faebe9;--warnc:#8a6100;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.62 var(--sans);-webkit-text-size-adjust:100%}
:focus-visible{outline:2px solid var(--acc);outline-offset:2px;border-radius:4px}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
/* Rail + reading column. The rail filters the stack by register; it never
   changes what the apply block or the drip schedule cover — filtering is a
   view, not a scope. */
.shell{display:grid;grid-template-columns:12.5rem minmax(0,46rem);gap:2.4rem;
justify-content:center;padding:0 1rem}
.wrap{min-width:0;padding:0 0 6rem}
.rail{position:sticky;top:0;align-self:start;padding:2rem 0;max-height:100dvh;overflow-y:auto}
.rail h2{font-family:var(--sans);font-size:.68rem;text-transform:uppercase;
letter-spacing:.1em;color:var(--dim);margin:0 0 .6rem;padding-left:.6rem;font-weight:650}
.navitem{display:flex;justify-content:space-between;align-items:baseline;gap:.6rem;
width:100%;padding:.44rem .6rem;margin-bottom:.15rem;border-radius:8px;
border:1px solid transparent;background:transparent;color:var(--dim);
font:inherit;font-size:.86rem;cursor:pointer;text-align:left;transition:.12s}
.navitem:hover{background:var(--card);color:var(--fg)}
.navitem.on{background:var(--card);border-color:var(--line);color:var(--fg);font-weight:620}
.navitem .n{font-size:.74rem;font-variant-numeric:tabular-nums;flex:none}
.navitem .n .d{color:var(--up);font-weight:650}
.railfoot{margin-top:1rem;padding:.7rem .6rem 0;border-top:1px solid var(--line);
font-size:.74rem;color:var(--dim);line-height:1.5}
@media(max-width:860px){
  .shell{grid-template-columns:minmax(0,1fr);gap:0;max-width:46rem;margin:0 auto}
  .rail{padding:.6rem 0;display:flex;gap:.4rem;overflow-x:auto;z-index:6;
    background:var(--bg);border-bottom:1px solid var(--line);max-height:none;
    scrollbar-width:none}
  .rail::-webkit-scrollbar{display:none}
  .rail h2,.railfoot{display:none}
  .navitem{width:auto;flex:none;white-space:nowrap;margin:0;
    border-color:var(--line);background:var(--card)}
}
header.top{padding:1.6rem 0 1rem;border-bottom:1px solid var(--line);margin-bottom:1.5rem}
h1{font-size:1.35rem;margin:0 0 .3rem;letter-spacing:-.01em}
.sub{color:var(--dim);font-size:.87rem;margin:0}
.counts{display:flex;gap:1.2rem;flex-wrap:wrap;margin-top:.9rem;font-size:.83rem}
.counts b{font-size:1.15rem;display:block;font-weight:650}
.counts span{color:var(--dim)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:1.3rem 1.4rem;margin:0 0 1.4rem}
.card.up{border-color:var(--up);box-shadow:inset 3px 0 0 var(--up)}
.card.down{border-color:var(--down);box-shadow:inset 3px 0 0 var(--down);opacity:.55}
.chead{display:flex;justify-content:space-between;align-items:center;gap:1rem;margin-bottom:.7rem}
.crumbs{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap}
.reg{font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;padding:.16rem .5rem;
border-radius:99px;background:var(--line);color:var(--dim);font-weight:600}
.reg-note{background:#dbe9f5;color:#1c4e7f}
.reg-newsletter{background:#f2e6d0;color:#7a5310}
@media(prefers-color-scheme:dark){.reg-note{background:#1b3348;color:#9cc8ee}
.reg-newsletter{background:#3a2f1c;color:#e0be7a}}
.num{color:var(--dim);font-size:.75rem}
.flag{font-size:.68rem;color:var(--warnc);border:1px solid currentColor;
padding:.1rem .45rem;border-radius:99px}
.thumbs{display:flex;gap:.4rem;flex:none}
.thumbs button{font-size:1.15rem;line-height:1;background:transparent;cursor:pointer;
border:1px solid var(--line);border-radius:9px;padding:.42rem .6rem;transition:.12s}
.thumbs button:hover{transform:translateY(-1px)}
.card.up .tu{background:var(--upbg);border-color:var(--up)}
.card.down .td{background:var(--downbg);border-color:var(--down)}
.kicker{font-size:.7rem;text-transform:uppercase;letter-spacing:.1em;color:var(--dim)}
h2{font-family:var(--serif);font-size:1.5rem;line-height:1.22;margin:.25rem 0 .5rem;
letter-spacing:-.01em;text-wrap:balance;font-weight:600}
.tagline{font-family:var(--serif);color:var(--dim);margin:0 0 1rem;font-size:1.02rem}
.seo{background:var(--bg);border:1px dashed var(--line);border-radius:8px;
padding:.6rem .8rem;margin-bottom:1rem;font-size:.85rem}
.seo .lbl{font-size:.66rem;text-transform:uppercase;letter-spacing:.08em;color:var(--dim)}
.seo .len{float:right;font-size:.7rem;font-weight:600}
.seo .len.ok{color:var(--up)}.seo .len.warn{color:var(--warnc)}
.seo p{margin:.35rem 0 0;color:var(--fg)}
.bullets{margin:0 0 1.1rem;padding-left:1.15rem}
.bullets li{margin:.28rem 0}
.body{font-family:var(--serif);font-size:1.02rem;line-height:1.66}
.body h3{font-family:var(--sans);font-size:.78rem;text-transform:uppercase;
letter-spacing:.09em;color:var(--dim);margin:1.5rem 0 .5rem;font-weight:650}
.body p{margin:0 0 .75rem}
.body ul,.body ol{margin:0 0 .8rem;padding-left:1.3rem}
.body li{margin:.3rem 0}
details{margin-top:.9rem;font-size:.87rem;border-top:1px solid var(--line);padding-top:.7rem}
summary{cursor:pointer;color:var(--acc);font-size:.8rem}
details p{margin:.55rem 0}
.stamp{color:var(--dim);font-size:.78rem;font-style:italic}
.slot{margin-top:.9rem;font-size:.82rem;color:var(--up);font-weight:600;min-height:1.2em}
/* Redaction. Struck through, not blacked out — the reviewer has to READ the
   thing to judge whether it should be withheld, and a censor's block hides
   exactly that. Amber rather than red: this is "look at me", not "error". */
s.red{text-decoration:line-through;text-decoration-thickness:2px;
text-decoration-color:var(--down);background:var(--downbg);
border-radius:3px;padding:0 .12em;cursor:help}
s.red:focus-visible{outline:2px solid var(--acc);outline-offset:1px}
sup.redk{font:600 .62em/1 var(--sans);color:var(--down);
margin-left:.2em;letter-spacing:.04em;text-transform:uppercase;vertical-align:super}
.redpanel{background:var(--downbg);border:1px solid var(--down);border-radius:8px;
padding:.6rem .8rem;margin:.8rem 0 0;font-size:.83rem}
.redpanel>summary{cursor:pointer;font-weight:640;color:var(--down)}
.redpanel .rnote{margin:.5rem 0 .6rem;color:var(--dim);line-height:1.5}
.redpanel ul{margin:0;padding-left:0;list-style:none}
.redpanel li{display:grid;grid-template-columns:auto 1fr;gap:.15rem .5rem;
padding:.45rem 0;border-top:1px dotted var(--line)}
.redpanel .rk{font:600 .72rem/1.5 var(--sans);text-transform:uppercase;
letter-spacing:.04em;color:var(--down)}
.redpanel code{font:.78rem var(--mono);background:var(--bg);border:1px solid var(--line);
border-radius:3px;padding:.05rem .3rem;overflow-wrap:anywhere}
.redpanel .rw{grid-column:1/-1;color:var(--dim);line-height:1.45}
.redpanel .rp{grid-column:1/-1;font:.7rem var(--mono);color:var(--dim)}
/* Scanned-and-clean is worth saying out loud: it is the difference between
   "nothing found" and "never looked". */
.redclean{margin:.7rem 0 0;font-size:.78rem;color:var(--dim)}
.redclean::before{content:"\2713\a0";color:var(--up);font-weight:700}
.apply{position:sticky;bottom:0;background:var(--card);border-top:2px solid var(--line);
margin:2rem -1rem 0;padding:1rem 1rem 1.2rem}
.apply h3{margin:0 0 .5rem;font-size:.95rem}
.apply pre{background:var(--bg);border:1px solid var(--line);border-radius:8px;
padding:.8rem;overflow-x:auto;font-family:var(--mono);font-size:.76rem;line-height:1.6;
max-height:14rem;margin:0}
.bar{display:flex;gap:.6rem;align-items:center;margin-bottom:.6rem;flex-wrap:wrap}
.bar button{font:inherit;font-size:.8rem;padding:.4rem .8rem;border-radius:8px;
border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer}
.bar button.primary{background:var(--acc);color:#fff;border-color:var(--acc)}
.tally{font-size:.8rem;color:var(--dim);margin-left:auto}
/* On a phone the apply bar is pinned over the cards you still have to read,
   so it stays compact: the command list scrolls inside a short box rather
   than growing with every approval, and the tally drops to its own line
   instead of orphaning itself against the right edge. */
@media(max-width:860px){
  .apply{margin:1.6rem -1rem 0;padding:.7rem .9rem .9rem}
  .apply h3{font-size:.85rem;margin:0}
  .apply pre{max-height:5.5rem;font-size:.72rem;padding:.6rem;line-height:1.5}
  .bar{gap:.45rem;margin-bottom:.5rem}
  .tally{margin-left:0;flex-basis:100%;order:3;font-size:.75rem}
  .bar button{padding:.45rem .85rem}
}
.empty{border:1px dashed var(--line);border-radius:12px;padding:2rem 1.4rem;text-align:center;color:var(--dim)}
.empty code{background:var(--card);padding:.15rem .4rem;border-radius:4px;font-size:.85em}
.xlink{display:inline-block;margin-top:.9rem;font-size:.8rem;color:var(--acc);
text-decoration:none;border-bottom:1px solid transparent}
.xlink:hover{border-bottom-color:currentColor}
"""

# The queue view. Read-only on purpose: it reports what release.js and
# promote_draft.py will act on, and the slug column is the handle both of
# them take. Nothing here mutates — a wrong click on a release schedule is
# expensive, and this page is the thing you consult when you're unsure.
QUEUE_CSS = """
.qwrap{max-width:60rem;margin:0 auto;padding:0 1rem 4rem}
.ro{display:inline-flex;align-items:center;gap:.4rem;font-size:.7rem;
text-transform:uppercase;letter-spacing:.09em;color:var(--dim);
border:1px solid var(--line);border-radius:99px;padding:.2rem .6rem;margin-bottom:.9rem}
.tbox{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:.86rem}
th{text-align:left;font-size:.66rem;text-transform:uppercase;letter-spacing:.09em;
color:var(--dim);font-weight:650;padding:.75rem .8rem;border-bottom:1px solid var(--line);
white-space:nowrap;background:var(--bg)}
td{padding:.7rem .8rem;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
td.pos{color:var(--dim);font-variant-numeric:tabular-nums;width:2.2rem}
td.id{font-family:var(--mono);font-size:.78rem;white-space:nowrap}
td.id button{font:inherit;background:transparent;border:1px dashed var(--line);
border-radius:6px;padding:.15rem .4rem;color:var(--fg);cursor:copy}
td.id button:hover{border-style:solid;border-color:var(--acc)}
td.ttl{font-family:var(--serif);min-width:16rem;line-height:1.4}
td.dt{font-variant-numeric:tabular-nums;white-space:nowrap;font-size:.8rem}
td.dt .proj{color:var(--dim)}
.pill{display:inline-block;font-size:.66rem;text-transform:uppercase;letter-spacing:.07em;
font-weight:650;padding:.16rem .5rem;border-radius:99px;white-space:nowrap}
.pill.live{background:var(--upbg);color:var(--up)}
.pill.queued{background:var(--line);color:var(--dim)}
.qnote{font-size:.8rem;color:var(--dim);margin:1rem 0 0;line-height:1.6}
.qnote code{font-family:var(--mono);font-size:.92em;background:var(--card);
border:1px solid var(--line);border-radius:5px;padding:.1rem .35rem}
.qhead{padding:1.8rem 0 1.1rem}
"""

JS = """
const SLOTS = __SLOTS__;
const KEY = 'draft-review-v1';
const FKEY = 'draft-review-filter';
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch(e) { state = {}; }
let filter = localStorage.getItem(FKEY) || 'all';

const cards = [...document.querySelectorAll('.card')];
const navs = [...document.querySelectorAll('.navitem')];
if (!navs.some(n => n.dataset.reg === filter)) filter = 'all';

function fmt(iso){
  const d = new Date(iso + 'T12:00:00');
  return d.toLocaleDateString(undefined,{weekday:'short',month:'short',day:'numeric'});
}

function render(){
  let ups = 0, downs = 0, si = 0;
  const per = {};
  for (const c of cards){
    const slug = c.dataset.slug, reg = c.dataset.reg, v = state[slug];
    (per[reg] = per[reg] || {t:0, d:0}).t++;
    if (v) per[reg].d++;
    c.classList.toggle('up', v === 'up');
    c.classList.toggle('down', v === 'down');
    // Filtering hides cards; it never changes the schedule or the apply
    // block, so si advances over every thumbed-up card, visible or not.
    c.hidden = filter !== 'all' && reg !== filter;
    const slot = c.querySelector('[data-slot]');
    if (v === 'up'){
      ups++;
      slot.textContent = si < SLOTS.length
        ? '\\u2192 queued for ' + fmt(SLOTS[si])
        : '\\u2192 queued \\u2014 beyond the scheduled horizon';
      si++;
    } else {
      if (v === 'down') downs++;
      slot.textContent = '';
    }
  }
  for (const n of navs){
    const reg = n.dataset.reg;
    n.classList.toggle('on', reg === filter);
    n.setAttribute('aria-pressed', reg === filter);
    const s = reg === 'all'
      ? {t: cards.length, d: ups + downs}
      : (per[reg] || {t:0, d:0});
    n.querySelector('.n').innerHTML =
      (s.d ? '<span class="d">' + s.d + '</span>/' : '') + s.t;
  }
  document.getElementById('tally').textContent =
    ups + ' up \\u00b7 ' + downs + ' down \\u00b7 ' + (cards.length - ups - downs) + ' undecided';

  const up = cards.filter(c => state[c.dataset.slug] === 'up');
  const down = cards.filter(c => state[c.dataset.slug] === 'down');
  const L = [];
  // One line per verb, not one per item. The batch is the unit of decision, so
  // it should be the unit of paste — and promote_draft validates the whole set
  // before writing, so a bad slug refuses everything rather than half-applying.
  if (up.length){
    // .venv/bin/python, not bare `python`: there is no `python` on this box
    // (only python3 and the venv), so a pasted `python ...` line dies with
    // "command not found" — and because the slugs are continuation lines, each
    // one then fails as its own bogus command. Silent-looking, total failure.
    // Matches the spike line below, which always had it right. Fixed 2026-08-03
    // after a real paste did nothing.
    L.push('# Queue ' + up.length + ' \\u2014 from /opt/ai-agent-platform');
    L.push('.venv/bin/python tools/promote_draft.py \\\\');
    up.forEach((c,i) => L.push('  ' + c.dataset.slug + (i < up.length - 1 ? ' \\\\' : '')));
  }
  if (down.length){
    if (L.length) L.push('');
    // `rejected`, not `spiked`. Everything on this desk is at status `drafted`
    // by definition — a draft existing is what put it here — and `spiked` is
    // legal only from new|claimed, so every thumbs-down was refused until
    // `rejected` existed (added 2026-08-03). The two verdicts stay distinct on
    // purpose: spiked means the lead wasn't worth pursuing, rejected means it
    // was and the draft failed it. Only the second says anything about the
    // Writer, which is the signal worth keeping while the voice is tuned.
    L.push('# Reject ' + down.length + ' draft(s) \\u2014 from /opt/ai-agent-platform');
    down.forEach(c => L.push('.venv/bin/python -m pipelines.scout.lead_mark ' + c.dataset.lead + ' --to rejected --by editor'));
  }
  // Rebuild goes HERE, not last: everything above happens in one sitting, and
  // the release lines below are spread over weeks. This page is a snapshot with
  // nothing scheduling it, so the instant a verdict lands the counts and the
  // drip schedule describe the world as it was before you decided. Shipping the
  // refresh inside the block itself is the only way it doesn't get forgotten —
  // the operator pastes one thing, not one thing plus a habit.
  if (L.length){
    L.push('');
    L.push('# Then refresh this page \\u2014 your verdicts just made it stale:');
    L.push('.venv/bin/python tools/draft_review.py');
  }
  if (up.length){
    L.push('');
    L.push('# Later, one per release day \\u2014 from /opt/uzelhub-web:');
    L.push('node marketing/release.js --next');
    L.push('# then record the release in the lead ledger \\u2014 from /opt/ai-agent-platform:');
    L.push('.venv/bin/python tools/reconcile_published.py');
    L.push('#   releases the head of the queue, in the order above:');
    up.forEach((c,i) => L.push('#     ' + (SLOTS[i] || 'later') + '  ' + c.dataset.slug));
  }
  document.getElementById('cmds').textContent =
    L.length ? L.join('\\n') : 'Thumb a draft to build the apply block.';
}

document.addEventListener('click', e => {
  const b = e.target.closest('.thumbs button');
  if (!b) return;
  const slug = b.closest('.card').dataset.slug;
  state[slug] = state[slug] === b.dataset.v ? undefined : b.dataset.v;
  if (!state[slug]) delete state[slug];
  localStorage.setItem(KEY, JSON.stringify(state));
  render();
});

document.querySelector('.rail').addEventListener('click', e => {
  const n = e.target.closest('.navitem');
  if (!n) return;
  filter = n.dataset.reg;
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


def apply_live_status(drafts: list[dict], leads_path: Path) -> int:
    """Overwrite each draft's embedded lead status with the LEDGER's.

    The status inside a draft file is a snapshot frozen at draft time — it says
    `claimed` forever. Four leads were marked `rejected` and the desk still
    listed them as awaiting review, because it trusted the snapshot. The ledger
    is the only source of truth for a verdict, so read it every build.
    """
    if not leads_path.exists():
        return 0
    live = {l["id"]: l.get("status", "new") for l in load_leads(leads_path)}
    n = 0
    for d in drafts:
        lead = d.get("lead") or {}
        cur = live.get(lead.get("id"))
        if cur and cur != lead.get("status"):
            lead["status"] = cur
            n += 1
    return n


def is_pending(d: dict, note_slugs: set) -> bool:
    """Still needs a verdict: not already promoted, and not already decided."""
    if d["note"]["slug"] in note_slugs:
        return False
    return (d.get("lead") or {}).get("status", "drafted") not in DECIDED


def build(drafts: list[dict], notes: list[dict], slots: list[int], today: dt.date) -> str:
    queued = [n for n in notes if not n.get("published")]
    released = [n for n in notes if n.get("published")]
    note_slugs = {n.get("slug") for n in notes}
    pending = [d for d in drafts if is_pending(d, note_slugs)]
    last = max((n["published"] for n in released), default=None)

    dates = drip_slots(notes, slots, max(len(pending), 1), today)
    slot_json = json.dumps([d.isoformat() for d in dates])

    if pending:
        cards = "".join(render_card(d, i + 1) for i, d in enumerate(pending))
    else:
        cards = (
            '<div class="empty"><p><b>No drafts waiting.</b></p>'
            "<p>The Writer takes assignments — it drafts leads already marked "
            "<code>claimed</code>. Claim a few, run the desk, then rebuild this page:</p>"
            "<p><code>python -m pipelines.writer &lt;lead-id&gt;</code></p></div>"
        )

    css = CSS
    js = JS.replace("__SLOTS__", slot_json)
    names = [k for k, v in sorted(WEEKDAYS.items(), key=lambda kv: kv[1]) if v in slots]

    # Rail rows: only registers actually present, in the order the newsroom
    # thinks about them (NEWSROOM §Content types), so the nav doesn't shuffle
    # between builds.
    order = ["note", "newsletter", "blog", "ticker"]
    present = {d.get("lead", {}).get("register", "note") for d in pending}
    regs = [r for r in order if r in present] + sorted(present - set(order))
    labels = {"note": "Field notes", "newsletter": "Newsletter", "blog": "Blog", "ticker": "Ticker"}
    rows = "".join(
        f'<button class="navitem" data-reg="{html.escape(r)}" aria-pressed="false">'
        f'<span>{html.escape(labels.get(r, r.title()))}</span><span class="n"></span></button>'
        for r in regs
    )
    rail = (
        '<nav class="rail" aria-label="Filter by register"><h2>Registers</h2>'
        '<button class="navitem" data-reg="all" aria-pressed="true">'
        '<span>Everything</span><span class="n"></span></button>'
        f"{rows}"
        '<div class="railfoot">Filtering changes the view only — the schedule '
        "and apply block always cover every verdict.</div></nav>"
    )

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Draft review desk</title>
<style>{css}</style>
</head><body><div class="shell">
{rail}
<div class="wrap">
<header class="top">
  <h1>Draft review desk</h1>
  <p class="sub">Thumb up to queue, thumb down to spike. Queuing is not publishing —
  the drip valve still decides the day.</p>
  <div class="counts">
    <div><b>{len(pending)}</b><span>awaiting review</span></div>
    <div><b>{len(queued)}</b><span>already queued</span></div>
    <div><b>{len(released)}</b><span>live</span></div>
    <div><b>{last or '—'}</b><span>last release</span></div>
    <div><b>{'/'.join(names)}</b><span>weekly slots · {MIN_GAP_DAYS}d min gap</span></div>
  </div>
  <a class="xlink" href="queue.html">View the publication queue &rarr;</a>
</header>
{cards}
<div class="apply">
  <div class="bar">
    <h3>Apply block</h3>
    <button id="copy" class="primary">copy</button>
    <button id="reset">clear</button>
    <span class="tally" id="tally"></span>
  </div>
  <pre id="cmds"></pre>
</div>
</div></div><script>{js}</script></body></html>
"""


def build_queue(notes: list[dict], slots: list[int], today: dt.date) -> str:
    """The actual queue as it stands in notes.json — released first, then the
    line waiting on the drip valve."""
    released = sorted((n for n in notes if n.get("published")), key=lambda n: n["published"])
    queued = [n for n in notes if not n.get("published")]
    dates = drip_slots(notes, slots, max(len(queued), 1), today)

    rows = []
    for i, n in enumerate(released, 1):
        rows.append((i, n, "live", n["published"], False))
    for j, n in enumerate(queued):
        proj = dates[j].isoformat() if j < len(dates) else None
        rows.append((len(released) + j + 1, n, "queued", proj, True))

    trs = []
    for pos, n, status, date, projected in rows:
        slug = n.get("slug", "")
        date_cell = (
            f'<span class="proj">{date} (projected)</span>' if projected and date
            else (date or '<span class="proj">unscheduled</span>')
        )
        trs.append(
            f'<tr><td class="pos">{pos}</td>'
            f'<td class="id"><button data-copy="{html.escape(slug)}" '
            f'title="Copy id">{html.escape(slug)}</button></td>'
            f'<td class="ttl">{html.escape(n.get("title", ""))}</td>'
            f'<td><span class="pill {status}">{status}</span></td>'
            f'<td class="dt">{date_cell}</td></tr>'
        )

    body = (
        f'<div class="tbox"><table><thead><tr><th></th><th>id</th><th>title</th>'
        f"<th>status</th><th>date</th></tr></thead><tbody>{''.join(trs)}</tbody></table></div>"
        if trs else '<div class="empty">Nothing in notes.json yet.</div>'
    )

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Publication queue</title>
<style>{CSS}{QUEUE_CSS}</style>
</head><body><div class="qwrap">
<header class="qhead">
  <div class="ro">read-only</div>
  <h1>Publication queue</h1>
  <p class="sub">{len(released)} live &middot; {len(queued)} waiting on the drip valve.
  Projected dates assume the current slots and hold to release.js&rsquo;s
  {MIN_GAP_DAYS}-day minimum gap.</p>
</header>
{body}
<p class="qnote">The <b>id</b> column is the handle every server-side command takes &mdash;
<code>node marketing/release.js &lt;id&gt;</code> to release,
<code>.venv/bin/python tools/promote_draft.py &lt;id&gt;</code> to queue a draft. Click one to copy it.
A note is live iff it carries a <code>published</code> date, and only release.js writes one;
projected dates are this page&rsquo;s arithmetic, not a commitment stored anywhere.</p>
<a class="xlink" href="index.html">&larr; Draft review desk</a>
</div>
<script>
document.addEventListener('click', async e => {{
  const b = e.target.closest('[data-copy]');
  if (!b) return;
  try {{ await navigator.clipboard.writeText(b.dataset.copy); }} catch (err) {{ return; }}
  const o = b.textContent;
  b.textContent = 'copied';
  setTimeout(() => {{ b.textContent = o; }}, 900);
}});
</script>
</body></html>
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--slots", default="tue,fri", help="weekly publish days (default: tue,fri)")
    ap.add_argument("--drafts-dir", default=str(DRAFTS_DIR))
    ap.add_argument("--notes-path", default=str(NOTES_PATH))
    ap.add_argument("--leads-path", default=str(LEADS_PATH))
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--open", action="store_true", help="print a file:// URL too")
    args = ap.parse_args(argv)

    try:
        slots = sorted({WEEKDAYS[s.strip().lower()[:3]] for s in args.slots.split(",") if s.strip()})
    except KeyError as e:
        print(f"bad slot name {e} — use mon..sun", file=sys.stderr)
        return 1
    if not slots:
        print("need at least one weekly slot", file=sys.stderr)
        return 1

    drafts = load_drafts(Path(args.drafts_dir))
    notes = load_notes(Path(args.notes_path))
    refreshed = apply_live_status(drafts, Path(args.leads_path))
    today = dt.date.today()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(drafts, notes, slots, today), encoding="utf-8")

    queue_out = out.parent / "queue.html"
    queue_out.write_text(build_queue(notes, slots, today), encoding="utf-8")

    note_slugs = {n.get("slug") for n in notes}
    pending = len([d for d in drafts if is_pending(d, note_slugs)])
    decided = len([d for d in drafts
                   if (d.get("lead") or {}).get("status") in DECIDED
                   and d["note"]["slug"] not in note_slugs])
    live = len([n for n in notes if n.get("published")])
    extra = f", {decided} already decided" if decided else ""
    print(f"built {out}  ({pending} draft(s) awaiting review, {len(drafts)} found{extra})")
    if refreshed:
        print(f"  ({refreshed} draft(s) had a stale embedded status; the ledger won)")
    print(f"built {queue_out}  ({live} live, {len(notes) - live} queued)")
    if args.open:
        print(f"file://{out}")
        print(f"file://{queue_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
