"""The leads ledger — the Scout's product, the Editor's queue.

YAML by hand (no pyyaml on the box; same zero-dep spirit as generate.js's
flat-YAML parser). The Scout APPENDS leads with status: new and never edits
existing entries. The Editor flips status. Two contracts enforced in code,
not just prose:

  - Pineapple rule: dedup reads ids + pitches ONLY. Statuses (claimed/spiked)
    are never loaded, so an Editor spike cannot become Scout feedback.
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
#       new -> claimed -> drafted -> approved -> published;  spiked from new|claimed
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


def load_pitched(path: Path) -> list[dict]:
    """Past pitches for dedup — ids and pitch text ONLY, statuses deliberately
    not read (the pineapple rule, enforced by omission)."""
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
    return pitched


def append_leads(path: Path, leads: list[dict], model: str) -> int:
    filed = date.today()
    existing_ids = {p["id"] for p in load_pitched(path)}
    blocks = []
    for lead in leads:
        block = format_lead(lead, filed, model)
        lead_id = block.splitlines()[0].split("id: ", 1)[1]
        if lead_id in existing_ids:
            continue  # same slug filed same day — identical pitch, skip
        existing_ids.add(lead_id)
        blocks.append(block)
    if not blocks:
        return 0
    if not path.exists():
        path.write_text(HEADER, encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(blocks))
    return len(blocks)
