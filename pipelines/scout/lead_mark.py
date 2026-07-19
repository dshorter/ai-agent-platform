"""lead-mark — the ONLY mutation verb for the leads ledger. calendar-mark's
philosophy applied to pipelines/scout/state/leads.yaml:

    python -m pipelines.scout.lead_mark <lead-id> --to <state> --by <actor>

Applies exactly one forward-only lifecycle transition to exactly one lead:

    new ──> claimed ──> drafted ──> approved ──> published
     │         │
     └────────>└──> spiked

Each mark flips the status line and inserts a dated provenance stamp
(`<state>_on: YYYY-MM-DD (<actor>)`) directly after it — stamps accumulate,
so the ledger carries the story's full timeline (time-to-publish metrics
read straight off the file). `--on` backdates a stamp when recording history
(e.g. backfilling a lead that published before this verb existed).

Hard limits, enforced here and not by prompt discipline:
  * one lead, one transition per invocation; transitions are forward-only
    and validated against the table (a lead is never un-published, never
    re-keyed, never deleted).
  * the actor must match the transition (editor claims/spikes/approves,
    the writer pipeline stamps drafted, the publish step stamps published).
  * never touches any field but `status:` + its stamp lines; never edits
    outside the matched lead's block.
  * refuses loudly (non-zero exit + message), never loops.

Pineapple rule unaffected by construction: the Scout's dedup reads ids +
pitches only (leads.load_pitched) — it never sees statuses or stamps.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parent / "state" / "leads.yaml"

# state -> (set of legal prior states, required actor)
TRANSITIONS = {
    "claimed": ({"new"}, "editor"),
    "spiked": ({"new", "claimed"}, "editor"),
    "drafted": ({"claimed"}, "writer"),
    "approved": ({"drafted"}, "editor"),
    "published": ({"approved"}, "publisher"),
}


def mark(lead_id: str, to: str, by: str, on: str | None = None, path: Path | None = None) -> str:
    # LEDGER is resolved at call time, not bound as a default — a default
    # freezes the path at import and silently ignores test-time overrides
    # (learned the hard way: the first verification run marked the real file).
    path = path or LEDGER
    if to not in TRANSITIONS:
        sys.exit(f"REFUSED: unknown state '{to}' (legal: {', '.join(TRANSITIONS)})")
    legal_from, actor = TRANSITIONS[to]
    if by != actor:
        sys.exit(f"REFUSED: '{to}' is stamped by {actor}, not {by}")
    stamp_date = on or datetime.date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp_date):
        sys.exit("REFUSED: --on must be YYYY-MM-DD")

    text = path.read_text(encoding="utf-8")
    m = re.search(rf"^  - id: {re.escape(lead_id)}$", text, re.M)
    if not m:
        sys.exit(f"REFUSED: no lead with id {lead_id}")
    nxt = re.search(r"^  - id: ", text[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(text)
    block = text[m.start():end]

    sm = re.search(r"^    status: (\S+)$", block, re.M)
    if not sm:
        sys.exit(f"REFUSED: lead {lead_id} has no status line (malformed block)")
    current = sm.group(1)
    if current == to:
        sys.exit(f"REFUSED: lead is already {to}")
    if current not in legal_from:
        sys.exit(
            f"REFUSED: {current} -> {to} is not a legal transition "
            f"({to} requires {' or '.join(sorted(legal_from))})"
        )
    if re.search(rf"^    {to}_on: ", block, re.M):
        sys.exit(f"REFUSED: lead already carries a {to}_on stamp")

    # Insert the stamp after the last existing stamp (or the status line),
    # so accumulated stamps read in chronological order.
    stamps = list(re.finditer(r"^    \w+_on: .+$", block, re.M))
    anchor = stamps[-1].end() if stamps else sm.end()
    new_block = (
        block[:sm.start()]
        + f"    status: {to}"
        + block[sm.end():anchor]
        + f"\n    {to}_on: {stamp_date} ({by})"
        + block[anchor:]
    )
    path.write_text(text[:m.start()] + new_block + text[end:], encoding="utf-8")
    return f"marked {to}: {lead_id} ({current} -> {to}, {stamp_date}, by {by})"


def main() -> None:
    ap = argparse.ArgumentParser(prog="lead-mark", description=__doc__.splitlines()[0])
    ap.add_argument("lead_id")
    ap.add_argument("--to", required=True, choices=sorted(TRANSITIONS))
    ap.add_argument("--by", required=True, choices=["editor", "writer", "publisher"])
    ap.add_argument("--on", help="backdate the stamp (YYYY-MM-DD) when recording history")
    a = ap.parse_args()
    print(mark(a.lead_id, a.to, a.by, a.on))


if __name__ == "__main__":
    main()
