#!/usr/bin/env python3
"""Assay the leads corpus — try to kill a claim about it with its own data.

The newsroom keeps generating claims about its own output: "the Scout only
files problems", "wins get demoted to ticker", "the wire spikes the boring
ones". Impressions like these are formed by scrolling, and scrolling samples
the top of a reverse-chronological list — which is to say it samples the
last two weeks and the slug layer, not the corpus.

This is the instrument for settling them. You name two lexicons, it splits
477 leads by which one they match, and cross-tabs the split four ways:

    register    — does the Scout route the two kinds differently?
    wire        — does the Wire Editor treat them differently?
    week        — is this a standing property or a recent drift?
    layer       — do the SLUGS say what the PITCHES say?

The last one is the one worth building a tool for. On 2026-08-19 a claim
that the Scout "never highlights accomplishments" died on the register and
wire tabs (wins outnumber problems 1.8:1 and get MORE blog treatment, and
the wire claims both at ~50%) and survived only on the layer tab: slugs read
116 negative to 61 positive, near-exactly the inverse of the pitch bodies
under them. The impression was right about what a person actually reads and
wrong about the corpus. No single number would have shown that.

Method, which matters more than the lexicons: state the claim, pick the tab
that could FALSIFY it, run it, and when it dies form the next claim from the
wreckage. A tab that merely agrees with you has told you nothing. This tool
prints every tab every time for exactly that reason — you do not get to
choose the flattering one after the fact.

Lexicons are crude on purpose: word lists, visible in the output, easy to
argue with. A classifier you cannot audit is not evidence.

    .venv/bin/python tools/leads_assay.py                       # the framing assay
    .venv/bin/python tools/leads_assay.py --list                # named assays
    .venv/bin/python tools/leads_assay.py --assay hedging
    .venv/bin/python tools/leads_assay.py --a-label agentic --a "agent,crew,director" \\
                                          --b-label plumbing  --b "timer,systemd,cron"
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import importlib.util
import os
import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from pipelines.writer.assignment import load_leads  # noqa: E402

LEADS_PATH = Path(os.environ.get("SCOUT_LEADS_PATH", _REPO / "pipelines" / "scout" / "state" / "leads.yaml"))
PROPOSALS_DIR = Path(os.environ.get("WIRE_EDITOR_STATE_DIR", _REPO / "pipelines" / "wire_editor" / "state")) / "proposals"

REGISTERS = ["ticker", "note", "newsletter", "blog"]
WIRE = ["claim", "spike", "hold"]

# Named assays. Each is (label_a, terms_a, label_b, terms_b, what it tests).
# Add one here rather than re-typing a lexicon into the shell — a claim worth
# testing twice is worth keeping the terms for.
ASSAYS: dict[str, tuple[str, str, str, str, str]] = {
    "framing": (
        "win",
        "shipped,ship,ships,live,landed,lands,works,working,held,holds,closed,closes,cut,"
        "faster,fixed,fix,proved,proves,proof,complete,completed,milestone,verified,green,"
        "resolved,first,wins,win",
        "problem",
        "bug,broke,broken,failed,failure,fails,wrong,missing,silently,silent,stale,leak,"
        "drift,gap,mistake,footgun,regression,hazard,poisoned,blind,invisible,forgot,almost,"
        "cannot,never,nobody,untested,unverified,orphan,collision,hang,dead",
        "does the Scout skew negative — and if so, at which layer?",
    ),
    "scope": (
        "cumulative",
        "since,weeks,week,months,month,cumulative,milestone,anniversary,finally,"
        "end-to-end,whole,across,over the,for the first time,by now,still",
        "momentary",
        "just,today,this session,this pass,now,minutes,moments,immediately,at once",
        "does anything narrate an arc, or is every lead same-day?",
    ),
    "hedging": (
        "asserted",
        "is,does,will,proves,shows,means,because,therefore",
        "hedged",
        "might,maybe,perhaps,possibly,could,seems,appears,arguably,unclear,unsure,suspect",
        "how confident does the Scout sound when it pitches?",
    ),
}


def _sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lexicon(terms: str) -> re.Pattern:
    """Word-boundary alternation over a comma list. Multi-word terms are
    allowed; hyphens are matched loosely so slug text and prose both hit."""
    parts = []
    for t in (x.strip().lower() for x in terms.split(",") if x.strip()):
        parts.append(re.escape(t).replace(r"\ ", r"[\s\-]+").replace(r"\-", r"[\s\-]+"))
    return re.compile(r"(?<![\w-])(?:" + "|".join(parts) + r")(?![\w-])")


def classify(text: str, a: re.Pattern, b: re.Pattern, la: str, lb: str) -> str:
    """Three-way, never two: the `mixed` bucket is what keeps a lexicon
    honest. A lead that hits both lists is not evidence for either side, and
    folding it into one would manufacture whichever result you wanted."""
    ha, hb = bool(a.search(text)), bool(b.search(text))
    if ha and hb:
        return "mixed"
    if ha:
        return la
    if hb:
        return lb
    return "neither"


def pitch_text(lead: dict) -> str:
    return (lead.get("pitch", "") + " " + lead.get("why_now", "")).lower()


def slug_text(lead: dict) -> str:
    # Strip the date prefix — `2026-08-19-...` would otherwise contribute
    # digits to every slug and nothing to the classification.
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", lead["id"]).replace("-", " ").lower()


def _tab(title: str, rows: list[str], cols: list[str], grid: dict, note: str = "") -> str:
    w = max((len(r) for r in rows), default=8) + 1
    head = f"{'':{w}}" + "".join(f"{c:>12}" for c in cols) + f"{'n':>8}"
    out = [f"\n  {title}", "  " + "-" * (len(head) + 2), "  " + head]
    for r in rows:
        n = sum(grid[r].get(c, 0) for c in cols)
        line = f"{r:{w}}" + "".join(f"{grid[r].get(c, 0):>12}" for c in cols) + f"{n:>8}"
        out.append("  " + line)
    if note:
        out.append(f"  {note}")
    return "\n".join(out)


def run(leads: list[dict], props: dict, la: str, ta: str, lb: str, tb: str, question: str) -> None:
    a, b = lexicon(ta), lexicon(tb)
    buckets = [la, lb, "mixed", "neither"]

    pitch_cls = {l["id"]: classify(pitch_text(l), a, b, la, lb) for l in leads}
    slug_cls = {l["id"]: classify(slug_text(l), a, b, la, lb) for l in leads}

    print(f"\nASSAY  {la} vs {lb}   over {len(leads)} leads")
    print(f"  question: {question}")
    print(f"  {la:<10} = {ta[:88]}{'…' if len(ta) > 88 else ''}")
    print(f"  {lb:<10} = {tb[:88]}{'…' if len(tb) > 88 else ''}")

    overall = collections.Counter(pitch_cls.values())
    tot = sum(overall[k] for k in (la, lb)) or 1
    print(f"\n  headline: {overall[la]} {la} / {overall[lb]} {lb} / {overall['mixed']} mixed "
          f"/ {overall['neither']} neither   ({overall[la] / tot:.0%} of the decided pitches are {la})")

    # 1. register — does the Scout route the two kinds to different shapes?
    g = collections.defaultdict(collections.Counter)
    for l in leads:
        g[pitch_cls[l["id"]]][l.get("register", "note")] += 1
    print(_tab("by REGISTER (how the Scout itself pitches each kind)", buckets, REGISTERS, g,
               "a real demotion shows up as a blog/ticker inversion between the two rows"))

    # 2. wire verdict — does the desk downstream treat them differently?
    if props:
        g = collections.defaultdict(collections.Counter)
        for l in leads:
            p = props.get(l["id"])
            if p:
                g[pitch_cls[l["id"]]][p.get("wire", "hold")] += 1
        seen = sum(sum(c.values()) for c in g.values())
        print(_tab(f"by WIRE VERDICT (of the {seen} leads the Wire Editor triaged)", buckets, WIRE, g,
                   "equal claim rates mean the desk is not the source of any skew"))
    else:
        print("\n  by WIRE VERDICT: no proposals artifacts found — skipped")

    # 3. week — standing property, or something that changed recently?
    g = collections.defaultdict(collections.Counter)
    for l in leads:
        d = l.get("filed")
        if not d:
            continue
        day = dt.date.fromisoformat(d)
        g[(day - dt.timedelta(days=day.weekday())).isoformat()][pitch_cls[l["id"]]] += 1
    weeks = sorted(g)
    print(_tab("by WEEK FILED (is this standing, or drift?)", weeks, buckets, g,
               "an impression formed by scrolling samples the LAST rows, not the corpus"))

    # 4. layer — the tab that earned this tool.
    g = collections.defaultdict(collections.Counter)
    for l in leads:
        g["pitch"][pitch_cls[l["id"]]] += 1
        g["slug"][slug_cls[l["id"]]] += 1
    print(_tab("by LAYER (do the slugs say what the pitches say?)", ["slug", "pitch"], buckets, g,
               "the slug layer is what a person browsing actually reads"))

    ps, pp = slug_cls, pitch_cls
    flipped = [l["id"] for l in leads if ps[l["id"]] == lb and pp[l["id"]] in (la, "mixed")]
    if flipped:
        print(f"\n  {len(flipped)} leads whose SLUG reads {lb} while the pitch does not. First 8:")
        for i in flipped[:8]:
            print(f"    {i}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--assay", default="framing", help="a named assay (see --list)")
    ap.add_argument("--list", action="store_true", help="list named assays and exit")
    ap.add_argument("--a-label"), ap.add_argument("--a", help="comma-separated terms for side A")
    ap.add_argument("--b-label"), ap.add_argument("--b", help="comma-separated terms for side B")
    ap.add_argument("--leads-path", default=str(LEADS_PATH))
    ap.add_argument("--proposals-dir", default=str(PROPOSALS_DIR))
    args = ap.parse_args(argv)

    if args.list:
        for name, (la, _ta, lb, _tb, q) in ASSAYS.items():
            print(f"  {name:<10} {la} vs {lb:<12} — {q}")
        return 0

    if args.a and args.b:
        la, ta, lb, tb = (args.a_label or "A"), args.a, (args.b_label or "B"), args.b
        question = "ad-hoc"
    else:
        if args.assay not in ASSAYS:
            print(f"no such assay: {args.assay} (see --list)", file=sys.stderr)
            return 1
        la, ta, lb, tb, question = ASSAYS[args.assay]

    leads = load_leads(Path(args.leads_path))
    if not leads:
        print(f"no leads in {args.leads_path}", file=sys.stderr)
        return 1

    pdir = Path(args.proposals_dir)
    paths = sorted(pdir.glob("*.yaml")) if pdir.is_dir() else []
    props = {}
    if paths:
        art = _sibling("wire_review").merge_artifacts(paths)
        props = {p["id"]: p for p in art["proposals"]}

    run(leads, props, la, ta, lb, tb, question)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
