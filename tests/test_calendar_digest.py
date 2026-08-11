"""Tests for the to-do digest — the projection injected into the Director's turn.

The digest makes a promise in its own header: *this is the whole open list, do
not go read calendar.ics to rebuild it*. That promise is the only reason the
Director stops grepping the raw file, so the test that matters most is that
every open todo actually appears. A digest that silently drops one is worse
than no digest, because the agent has been told not to go looking.

    .venv/bin/python -m pytest tests/test_calendar_digest.py -q
"""
from __future__ import annotations

import datetime
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_OPS = Path(__file__).resolve().parents[1] / "ops"


def _load():
    """ops/calendar-views is extensionless, so no finder locates it by name."""
    spec = importlib.util.spec_from_loader(
        "calendar_views", SourceFileLoader("calendar_views", str(_OPS / "calendar-views"))
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cv = _load()

TODAY = datetime.date(2026, 8, 11)
NOW = datetime.datetime(2026, 8, 11, 7, 0, tzinfo=cv.TZ)


def _todo(uid, summary, due=None, status="NEEDS-ACTION", desc=None, parent=None):
    lines = [f"UID:{uid}", f"SUMMARY:{summary}", f"STATUS:{status}"]
    if due:
        lines.append(f"DUE;VALUE=DATE:{due}")
    if desc:
        lines.append(f"DESCRIPTION:{desc}")
    if parent:
        lines.append(f"RELATED-TO;RELTYPE=PARENT:{parent}")
    body = "\n".join(lines)
    return f"BEGIN:VTODO\n{body}\nEND:VTODO\n"


def _calendar(*todos):
    return "BEGIN:VCALENDAR\nVERSION:2.0\n" + "".join(todos) + "END:VCALENDAR\n"


FIXTURE = _calendar(
    _todo("late@ai-agent-platform", "Ancient thing", "20260714"),
    _todo("today@ai-agent-platform", "Due right now", "20260811", desc="the detail"),
    _todo("soon@ai-agent-platform", "This week", "20260815"),
    _todo("later@ai-agent-platform", "Far off", "20260930"),
    _todo("undated@ai-agent-platform", "Someday"),
    _todo("done@ai-agent-platform", "Finished", "20260801", status="COMPLETED"),
    _todo("child@ai-agent-platform", "Subtask", "20260810",
          parent="late@ai-agent-platform"),
)


# ── the buckets ──────────────────────────────────────────────────────────────

def test_bucketize_splits_by_due_date():
    open_, buckets = cv.bucketize(cv.parse(FIXTURE), TODAY)
    got = {name: [c["UID"].split("@")[0] for c in items] for name, items in buckets.items()}
    assert got["Overdue"] == ["late", "child"]
    assert got["Due today"] == ["today"]
    assert got["Next 7 days"] == ["soon"]
    assert got["Later"] == ["later"]
    assert got["No due date"] == ["undated"]
    assert "done" not in [c["UID"].split("@")[0] for c in open_]  # COMPLETED is closed


# ── the promise: nothing dated goes missing ──────────────────────────────────

@pytest.mark.parametrize("uid", ["late", "child", "today", "soon"])
def test_every_actionable_todo_appears_with_its_uid(uid):
    """Overdue / today / this week are listed individually, uid included, because
    the uid is what calendar_mark takes when the Director proposes closing one."""
    digest = cv.emit_digest(cv.parse(FIXTURE), now=NOW)
    assert f"uid={uid}@ai-agent-platform" in digest


def test_the_real_calendar_lists_every_open_dated_todo():
    """Against the live file, not a fixture — the drop this guards against is a
    size or clipping regression that only shows up at real scale."""
    comps = cv.parse((_OPS / "calendar.ics").read_text())
    _open, buckets = cv.bucketize(comps, datetime.date.today())
    digest = cv.emit_digest(comps)
    listed = [c for name in ("Overdue", "Due today", "Next 7 days") for c in buckets[name]]
    missing = [c["UID"] for c in listed if f'uid={c["UID"]}' not in digest]
    assert not missing, f"digest dropped {len(missing)} todo(s): {missing}"


def test_later_and_undated_are_counted_not_listed():
    digest = cv.emit_digest(cv.parse(FIXTURE), now=NOW)
    assert "uid=later@" not in digest and "uid=undated@" not in digest
    assert "Later 1" in digest and "No due date 1" in digest


def test_completed_todos_are_absent():
    assert "Finished" not in cv.emit_digest(cv.parse(FIXTURE), now=NOW)


# ── shape ────────────────────────────────────────────────────────────────────

def test_relations_and_descriptions_ride_along():
    digest = cv.emit_digest(cv.parse(FIXTURE), now=NOW)
    assert "↳ subtask of Ancient thing" in digest  # the parent by name, not uid
    assert "the detail" in digest                  # description on a today item


def test_description_is_clipped():
    long_desc = "x" * (cv.DIGEST_DESC_CHARS + 200)
    digest = cv.emit_digest(
        cv.parse(_calendar(_todo("big@ai-agent-platform", "Big", "20260811", desc=long_desc))),
        now=NOW,
    )
    assert "x" * cv.DIGEST_DESC_CHARS + "…" in digest
    assert "x" * (cv.DIGEST_DESC_CHARS + 1) not in digest


def test_header_states_the_list_is_complete():
    """The instruction not to re-read the source is load-bearing: without it the
    Director burned 8 of 12 tool calls rebuilding this by hand (2026-08-11)."""
    digest = cv.emit_digest(cv.parse(FIXTURE), now=NOW)
    assert "do not read or grep calendar.ics" in digest


def test_digest_stays_prompt_sized():
    """It rides on every turn, reactive chat included. A slow creep past this is
    a real cost regression, not a style question."""
    digest = cv.emit_digest(cv.parse((_OPS / "calendar.ics").read_text()))
    assert len(digest) < 20_000, f"digest is {len(digest)} chars — trim it or cut descriptions"
