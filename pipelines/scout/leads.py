"""The leads ledger — the Scout's product, the Editor's queue.

YAML by hand (no pyyaml on the box; same zero-dep spirit as generate.js's
flat-YAML parser). The Scout APPENDS leads with status: new and never edits
existing entries. The Editor flips status. Two contracts enforced in code,
not just prose:

  - Pineapple rule: dedup reads ids + pitches ONLY. Statuses (claimed/spiked/rejected)
    are never loaded, so an Editor spike cannot become Scout feedback. The
    2026-09-04 pitch digest shortens what is read; it does not widen it. There
    is still no pattern here that matches a status, which is the whole of the
    enforcement — the rule is broken by ADDING a regex, a visible act in a diff.
  - copyDraft discipline: every lead carries provenance (model, filed date)
    and `redaction: required` — nothing sourced from session logs publishes
    without a hard secret/PII scrub AND Editor approval. That is also why the
    ledger lives in the gitignored state dir: origin is a public repo, and a
    push is a publish.
"""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

HEADER = """\
# Scout leads — the unpromoted story queue (NEWSROOM v1: ledger pattern).
#
# Contract:
#   - The Scout appends leads with status: new. It never edits or removes entries.
#   - Lifecycle (forward-only, one dated stamp per transition, mutations ONLY
#     via `python -m pipelines.scout.lead_mark`, never freehand):
#       new -> claimed -> drafted -> approved -> published;  spiked from new|claimed;
#       rejected from drafted (the draft failed; distinct from spiked, which
#       means the lead was never worth pursuing)
#     Editor claims/spikes/approves; the writer pipeline stamps drafted;
#     the publish step stamps published. Drafted leads may be redrafted.
#   - Spikes are NOT feedback. The Scout reads back ids + pitches only (dedup);
#     it never sees statuses or stamps. The next pass must be no less reckless.
#   - REDACTION (absolute): session logs contain credentials, keys, PII. Nothing
#     derived from them publishes without a hard scrub AND Editor approval.
#     `redaction: required` marks that gate; it is not advisory.
leads:
"""


def _block_scalar(text: str, indent: str) -> str:
    clean = " ".join(text.split())
    return f">-\n{indent}  " + _wrap(clean, indent)


def _wrap(text: str, indent: str, width: int = 88) -> str:
    words, lines, line = text.split(), [], ""
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        lines.append(line)
    return f"\n{indent}  ".join(lines)


def format_lead(lead: dict, filed: date, model: str) -> str:
    ind = "    "
    slug = re.sub(
        r"-+", "-", re.sub(r"[^a-z0-9-]", "-", str(lead.get("slug", "untitled")).lower())
    ).strip("-")[:60] or "untitled"
    parts = [
        f"  - id: {filed.isoformat()}-{slug}",
        f"{ind}filed: {filed.isoformat()}",
        f"{ind}status: new",
        f"{ind}register: {lead.get('register', 'note')}",
        f"{ind}agent_span: {int(lead.get('agent_span', 1))}",
        f"{ind}pitch: {_block_scalar(str(lead.get('pitch', '')), ind)}",
        f"{ind}why_now: {_block_scalar(str(lead.get('why_now', '')), ind)}",
        f"{ind}sources:",
    ]
    for src in lead.get("sources", []) or ["(none given)"]:
        parts.append(f"{ind}  - {' '.join(str(src).split())}")
    parts.append(f"{ind}redaction: required")
    parts.append(f"{ind}model: {model}")
    return "\n".join(parts) + "\n"


def _digest(pitch: str, limit: int) -> str:
    """The first sentence of a pitch, or the first `limit` chars on a word
    boundary — whichever comes first. Marked with an ellipsis so the model can
    see it is reading a digest rather than a short pitch."""
    pitch = pitch.strip()
    if limit <= 0 or len(pitch) <= limit:
        return pitch
    window = pitch[:limit]
    stop = max(window.rfind(". "), window.rfind("? "), window.rfind("! "))
    if stop >= limit // 3:                      # a sentence ended in range
        return window[: stop + 1]
    cut = window.rfind(" ")
    return (window[:cut] if cut > 0 else window).rstrip(",;:—- ") + " …"


def load_pitched(path: Path, pitch_chars: int | None = None) -> list[dict]:
    """Past pitches for dedup — ids and pitch text ONLY, statuses deliberately
    not read (the pineapple rule, enforced by omission).

    `pitch_chars` truncates each pitch to a digest. **This is the dominant term
    in the synthesis prompt's cost**, not the jewels it reasons over: the
    payload measured 477 entries / 299,322 chars / ~74,830 tokens on
    2026-08-23, and it grows every time a lead is filed, forever, because
    dedup memory can never be pruned (scout-mining-economics.md §Where the
    money actually goes). Synthesis cost rose 4x in six weeks on that
    mechanism alone.

    Full pitch text was never shown to be necessary for the job. The question
    — "whether a near-identical check needs full pitch text or just a slug and
    a first line" — is named as open in the same document. A digest keeps what
    dedup actually matches on: the id is already a semantic slug, and the first
    sentence carries the story's claim. Pass None for the pre-2026-09 full-text
    behaviour, which is what the measurement below should be compared against.

    **Verify before resuming the ambient pass**, since this changes what the
    model is shown: run one --synthesize --dry-run at the configured digest and
    one at None over the same jewels, and check the second list does not
    re-pitch anything already in the ledger. Dry runs file nothing, so this
    costs two synthesis calls and no state.
    """
    if not path.exists():
        return []
    pitched, current = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^  - id: (.+)$", line)
        if m:
            current = {"id": m.group(1).strip(), "pitch": ""}
            pitched.append(current)
            continue
        if current is not None:
            if re.match(r"^    pitch: ", line):
                current["_in_pitch"] = True
                continue
            if current.get("_in_pitch"):
                if re.match(r"^      \S", line):
                    current["pitch"] += " " + line.strip()
                    continue
                current.pop("_in_pitch", None)
    for p in pitched:
        p.pop("_in_pitch", None)
        p["pitch"] = p["pitch"].strip()
        if pitch_chars is not None:
            p["pitch"] = _digest(p["pitch"], pitch_chars)
    return pitched


def append_leads(
    path: Path, leads: list[dict], model: str, pitch_chars: int = 240
) -> int:
    filed = date.today()
    existing_ids = {p["id"] for p in load_pitched(path)}
    blocks, filed_leads = [], []
    for lead in leads:
        block = format_lead(lead, filed, model)
        lead_id = block.splitlines()[0].split("id: ", 1)[1]
        if lead_id in existing_ids:
            continue  # same slug filed same day — identical pitch, skip
        existing_ids.add(lead_id)
        blocks.append(block)
        filed_leads.append(lead)
    if not blocks:
        return 0
    if not path.exists():
        path.write_text(HEADER, encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(blocks))
    # Mirror into the dedup index in the same call. The ledger is still the
    # source of truth — if this write is ever missed, --rebuild-index restores
    # it from the ledger — but doing both here is what keeps them in step
    # without a reconciliation step nobody would run.
    append_pitched_index(index_path_for(path), filed_leads, filed, model, pitch_chars)
    return len(blocks)


# ---------------------------------------------------------------------------
# The pitched index — the Scout's dedup memory, as its own file
# ---------------------------------------------------------------------------
# Three concerns were sharing one file, with lifetimes that disagree: the
# Editor's working queue wants pruning, this dedup memory can never be pruned
# (pruning re-admits duplicates), and the record of what prospecting found
# wants immutability. leads.yaml stays the record — append-only, statuses
# stamped in place, unchanged. This file carries the dedup concern alone.
#
# WHY THE INDEX IS DERIVED, NOT A THIRD SOURCE OF TRUTH: three independent
# files would make a lifecycle transition MOVE a lead between them, which is a
# two-file write that can leave a lead in both or neither. Today a transition
# is one in-place stamp with no such hazard, and lead_mark's guarantees rest on
# that. A derived index has no move: if it is ever lost or wrong, rebuild it.
#
# WHY IT IS WORTH A FILE ANYWAY: the digest is written to disk rather than
# computed at read time, so the file the Scout reads PHYSICALLY CONTAINS no
# status, no stamp, no verdict. Enforcement moves from "load_pitched has no
# regex for status" — true, and dependent on nobody adding one — to "the bytes
# are not there". That is the pineapple rule in file shape rather than in code
# discipline, which is the stronger of the two.
#
# The queue/archive split is NOT built, deliberately. Measured 2026-09-04: it
# would put 472 of 477 leads in the queue and 5 in the archive, because 470
# leads sit `new`. The queue is oversized because gate ① has not been worked,
# not because terminal leads are mixed into it, so that cut separates nothing
# yet. Build it when triage is moving and it has something to separate.

PITCHED_HEADER = """\
# Scout dedup memory — every lead ever pitched, as id + digest.
#
# DERIVED from leads.yaml. Rebuild at any time:
#     python -m pipelines.scout.leads --rebuild-index
#
# Contract:
#   - Append-only and never pruned: forgetting a pitch re-admits it as a
#     "new" lead on the next pass.
#   - Carries NO status, NO stamp, NO verdict, and must never be taught to.
#     This is the file Scout synthesis reads, and the pineapple rule says no
#     editor signal may reach the Scout. Here that is enforced by the bytes
#     being absent, not by a reader choosing not to look.
#   - The pitch is a DIGEST, not the full text — the full pitch lives in
#     leads.yaml. See leads.load_pitched for why and for how to verify it.
leads:
"""


def index_path_for(ledger_path: Path) -> Path:
    """The dedup index that sits beside a ledger. Derived from the ledger's own
    location so every existing call site keeps working unchanged."""
    return ledger_path.with_name("pitched.yaml")


def format_pitched(lead_id: str, pitch: str) -> str:
    """One index entry, in the ledger's own shape.

    Deliberately the same YAML the ledger uses, so `load_pitched` parses this
    file unchanged — one parser, one format, and the index cannot drift into a
    second dialect that needs a second reader.
    """
    ind = "    "
    return f"  - id: {lead_id}\n{ind}pitch: {_block_scalar(pitch, ind)}\n"


def write_pitched_index(
    ledger_path: Path, index_path: Path | None = None, pitch_chars: int = 240
) -> int:
    """(Re)build the whole index from the ledger. Returns entries written."""
    index_path = index_path or index_path_for(ledger_path)
    entries = load_pitched(ledger_path, pitch_chars)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        PITCHED_HEADER + "".join(format_pitched(e["id"], e["pitch"]) for e in entries),
        encoding="utf-8",
    )
    return len(entries)


def append_pitched_index(
    index_path: Path, leads: list[dict], filed: date, model: str, pitch_chars: int = 240
) -> int:
    """Append newly-filed leads to the index, mirroring append_leads.

    Takes the same raw lead dicts append_leads takes and derives the id the
    same way, so the two files cannot disagree about what a lead is called.
    """
    existing = {e["id"] for e in load_pitched(index_path)} if index_path.exists() else set()
    blocks = []
    for lead in leads:
        lead_id = format_lead(lead, filed, model).splitlines()[0].split("id: ", 1)[1]
        if lead_id in existing:
            continue
        existing.add(lead_id)
        blocks.append(format_pitched(lead_id, _digest(str(lead.get("pitch", "")), pitch_chars)))
    if not blocks:
        return 0
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if not index_path.exists():
        index_path.write_text(PITCHED_HEADER, encoding="utf-8")
    with index_path.open("a", encoding="utf-8") as fh:
        fh.write("".join(blocks))
    return len(blocks)


def load_dedup_memory(ledger_path: Path, pitch_chars: int = 240) -> list[dict]:
    """What synthesis is shown about leads already pitched.

    Prefers the index, falls back to the ledger. The fallback is not a
    convenience — it is what makes the index safe to adopt: an estate that has
    not run --rebuild-index yet, or a fresh checkout, or a test with only a
    ledger, all keep working and simply pay the old cost. There is no window in
    which dedup silently reads nothing, which would re-pitch the entire
    backlog.
    """
    index = index_path_for(ledger_path)
    if index.exists():
        return load_pitched(index)      # already digested on disk
    return load_pitched(ledger_path, pitch_chars)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(prog="leads", description=__doc__)
    ap.add_argument("--rebuild-index", action="store_true",
                    help="regenerate pitched.yaml from leads.yaml")
    ap.add_argument("--ledger", type=Path,
                    default=Path(__file__).resolve().parent / "state" / "leads.yaml")
    ap.add_argument("--digest", type=int, default=240,
                    help="chars of each pitch to keep (default 240)")
    args = ap.parse_args()
    if not args.rebuild_index:
        ap.print_help()
        raise SystemExit(1)
    index = index_path_for(args.ledger)
    n = write_pitched_index(args.ledger, index, args.digest)
    ledger_size = args.ledger.stat().st_size if args.ledger.exists() else 0
    print(f"rebuilt {index} — {n} entries, "
          f"{index.stat().st_size:,} bytes (ledger {ledger_size:,})")


if __name__ == "__main__":
    main()
