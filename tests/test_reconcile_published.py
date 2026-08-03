"""Tests for reconcile_published — the lifecycle's last stamp.

Why this file exists: the ledger defines `published` (from `approved`, actor
`publisher`) but nothing ever called it — release.js stamps notes.json and
has never heard of the ledger, so every released lead sat at `approved`
forever. Found 2026-08-03 while walking the pipeline order end to end.

The verb is meant to be pasted after every release, so the tests care as
much about what it does NOT do (re-stamp history, guess at unlinked notes,
touch queued entries) as what it does.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_spec = importlib.util.spec_from_file_location(
    "reconcile_published", _TOOLS / "reconcile_published.py"
)
_rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rp)


LEDGER = """\
leads:
  - id: lead-live
    filed: 2026-07-01
    status: {status}
    register: note
"""


def _world(tmp_path, status="approved", published="2026-08-01", linked=True):
    """A tiny newsroom: one draft, one note, one lead."""
    drafts = tmp_path / "drafts"
    drafts.mkdir()
    if linked:
        (drafts / "lead-live.json").write_text(
            json.dumps({"note": {"slug": "the-slug"}, "lead": {"id": "lead-live"}}),
            encoding="utf-8")
    notes = tmp_path / "notes.json"
    note = {"slug": "the-slug"}
    if published:
        note["published"] = published
    notes.write_text(json.dumps([note]), encoding="utf-8")
    ledger = tmp_path / "leads.yaml"
    ledger.write_text(LEDGER.format(status=status), encoding="utf-8")
    return drafts, notes, ledger


def test_released_approved_lead_gets_stamped_with_the_release_date(tmp_path):
    drafts, notes, ledger = _world(tmp_path)
    out = _rp.reconcile(drafts, notes, ledger)
    assert out == ["marked published: lead-live (approved -> published, 2026-08-01, by publisher)"]
    text = ledger.read_text()
    assert "    status: published" in text
    assert "    published_on: 2026-08-01 (publisher)" in text


def test_queued_note_is_not_a_release(tmp_path):
    """No published date = release.js hasn't spoken. Nothing moves."""
    drafts, notes, ledger = _world(tmp_path, published=None)
    assert _rp.reconcile(drafts, notes, ledger) == []
    assert "status: approved" in ledger.read_text()


def test_unlinked_note_is_reported_not_guessed(tmp_path):
    drafts, notes, ledger = _world(tmp_path, linked=False)
    out = _rp.reconcile(drafts, notes, ledger)
    assert out == ["skipped the-slug: no draft links it to a lead (pre-pipeline note)"]
    assert "status: approved" in ledger.read_text()


def test_second_run_is_silent(tmp_path):
    """Idempotence is the contract: this pastes after EVERY release."""
    drafts, notes, ledger = _world(tmp_path)
    _rp.reconcile(drafts, notes, ledger)
    assert _rp.reconcile(drafts, notes, ledger) == []
    assert ledger.read_text().count("published_on:") == 1


def test_release_the_ledger_never_saw_coming_refuses(tmp_path):
    """A published note whose lead never reached `approved` means a release
    bypassed the promote step — say so loudly, stamp nothing."""
    drafts, notes, ledger = _world(tmp_path, status="drafted")
    out = _rp.reconcile(drafts, notes, ledger)
    assert len(out) == 1 and out[0].startswith("REFUSED the-slug")
    assert "status: drafted" in ledger.read_text()


def test_dry_run_reports_without_stamping(tmp_path):
    drafts, notes, ledger = _world(tmp_path)
    out = _rp.reconcile(drafts, notes, ledger, dry_run=True)
    assert out == ["would mark published: lead-live (released 2026-08-01)"]
    assert "status: approved" in ledger.read_text()
