"""Read assignments off the leads ledger.

The Writer READS the ledger here and never writes it freehand — its one
sanctioned write is the `drafted` stamp via lead_mark after banking a draft
(leads.py contract: new -> claimed -> drafted -> approved -> published,
spiked from new|claimed, rejected from drafted; all transitions via lead_mark).
Unlike the Scout's
load_pitched (which deliberately reads ids+pitches only, per the pineapple
rule), the Writer legitimately reads whole leads: an assignment IS the full
record, status included. The pineapple rule protects the prospector's
aperture, not the rewrite desk's inputs."""
from __future__ import annotations

import re
from pathlib import Path

_LEAD_RE = re.compile(r"^  - id: (.+)$")
_FIELD_RE = re.compile(r"^    (\w+): ?(.*)$")
_SOURCE_RE = re.compile(r"^      - (.+)$")
_FOLD_RE = re.compile(r"^      (\S.*)$")


def load_leads(path: Path) -> list[dict]:
    """Parse the hand-rolled flat-YAML ledger (leads.py writes it; same
    zero-dep spirit reads it). Returns one dict per lead, folded scalars
    unwrapped."""
    leads: list[dict] = []
    cur: dict | None = None
    field: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            field = None
            continue
        m = _LEAD_RE.match(raw)
        if m:
            cur = {"id": m.group(1).strip(), "sources": []}
            leads.append(cur)
            field = None
            continue
        if cur is None:
            continue
        m = _FIELD_RE.match(raw)
        if m:
            key, val = m.group(1), m.group(2)
            if val == ">-":
                field = key
                cur[key] = ""
            elif key == "sources":
                field = "sources"
            else:
                field = None
                cur[key] = val
            continue
        if field == "sources":
            m = _SOURCE_RE.match(raw)
            if m:
                cur["sources"].append(m.group(1).strip())
                continue
        if field and field != "sources":
            m = _FOLD_RE.match(raw)
            if m:
                cur[field] = f"{cur[field]} {m.group(1).strip()}".strip()
    return leads


def find_lead(path: Path, lead_id: str) -> dict | None:
    return next((l for l in load_leads(path) if l["id"] == lead_id), None)
