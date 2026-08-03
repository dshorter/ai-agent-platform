#!/usr/bin/env python3
"""Record releases in the lead ledger — the lifecycle's missing last stamp.

The gap this closes: release.js (uzelhub-web) is what actually publishes a
note — it stamps the `published` ISO date in notes.json, which is the fact
that gates the page going live. But it is Node, lives in another repo, and
has never heard of the leads ledger. So nothing stamped a lead `published`,
and every released lead sat at `approved` forever: time-to-publish metrics
unreadable, the lifecycle's last transition defined but dead.

This verb reconciles after the fact rather than teaching release.js to
reach across repos: for every note in notes.json that carries a published
date, find the draft that links its slug to a lead, and if the ledger still
says `approved`, stamp `published` — backdated to the note's own published
date, via lead_mark, the only sanctioned mutation verb. Idempotent: a lead
already at `published` is passed over in silence, so running it twice (or
after every release, which is the intent) costs nothing.

The queue page's paste-block appends this command after each release.js
line — the operator pastes one thing, not one thing plus a habit.

    .venv/bin/python tools/reconcile_published.py
    .venv/bin/python tools/reconcile_published.py --dry-run

Notes with no linking draft (pre-pipeline history, e.g. the July field
notes hand-written before the Scout existed) are reported and skipped —
absence of provenance is stated, never guessed at.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from pipelines.scout.lead_mark import mark  # noqa: E402
from pipelines.writer.assignment import load_leads  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "promote_draft", Path(__file__).resolve().parent / "promote_draft.py"
)
_pd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pd)
load_drafts = _pd.load_drafts

DRAFTS_DIR = Path(os.environ.get("WRITER_DRAFTS_DIR", _REPO / "pipelines" / "writer" / "state" / "drafts"))
NOTES_PATH = Path(os.environ.get("UZELHUB_NOTES_PATH", "/opt/uzelhub-web/marketing/data/notes.json"))
LEADS_PATH = Path(os.environ.get("SCOUT_LEADS_PATH", _REPO / "pipelines" / "scout" / "state" / "leads.yaml"))


def reconcile(
    drafts_dir: Path = DRAFTS_DIR,
    notes_path: Path = NOTES_PATH,
    leads_path: Path = LEADS_PATH,
    dry_run: bool = False,
) -> list[str]:
    """Returns report lines; stamps unless dry_run. Loud on surprises,
    silent on already-recorded history."""
    slug_to_lead = {
        d["note"]["slug"]: d.get("lead", {}).get("id")
        for d in load_drafts(drafts_dir)
        if d.get("note", {}).get("slug")
    }
    leads = {l["id"]: l for l in load_leads(leads_path)} if leads_path.is_file() else {}
    out = []
    for note in json.loads(notes_path.read_text(encoding="utf-8")):
        slug, pub = note.get("slug", "?"), note.get("published")
        if not pub:
            continue  # queued, not released — release.js hasn't spoken yet
        lead_id = slug_to_lead.get(slug)
        if not lead_id:
            out.append(f"skipped {slug}: no draft links it to a lead (pre-pipeline note)")
            continue
        status = leads.get(lead_id, {}).get("status")
        if status == "published":
            continue  # already recorded — this verb is meant to re-run
        if status != "approved":
            out.append(
                f"REFUSED {slug}: lead {lead_id} is {status!r}, not approved — "
                "a release the ledger never saw coming; fix the ledger first"
            )
            continue
        if dry_run:
            out.append(f"would mark published: {lead_id} (released {pub})")
        else:
            out.append(mark(lead_id, to="published", by="publisher", on=pub, path=leads_path))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true", help="report without stamping")
    a = ap.parse_args()
    lines = reconcile(dry_run=a.dry_run)
    for line in lines:
        print(line)
    if not lines:
        print("ledger already agrees with notes.json — nothing to record")
    return 1 if any(l.startswith("REFUSED") for l in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
