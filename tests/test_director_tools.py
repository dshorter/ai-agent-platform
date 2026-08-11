"""Tests for the toolbox read ceilings — the alarm for a silent capability loss.

A clip is invisible from the outside. When ops/calendar.ics grew past the read
limit on 2026-08-03, nothing failed: the Director just started answering from a
partial file, and it took until 08-11 and a wrong-cause morning brief to notice.
The last test here is the alarm that was missing — it fails when a document the
agents actually read grows past what they can read.

    .venv/bin/python -m pytest tests/test_director_tools.py -q
"""
from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.director.tools import (
    MAX_READ_BYTES, MAX_TOOL_RESULT_CHARS, ToolBox,
)

_REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def box(tmp_path):
    return ToolBox([tmp_path])


# ── the two ceilings have to move together ───────────────────────────────────

def test_the_result_clip_leaves_room_for_the_truncation_notice():
    """dispatch() clips EVERY result to MAX_TOOL_RESULT_CHARS. A truncated read is
    MAX_READ_BYTES *plus* the notice, so equal ceilings mean the notice itself gets
    clipped off and replaced by the generic one — losing the byte counts precisely
    when a file is too big, which is the only time they matter. Caught by this
    suite when both were first set to 120k on 2026-08-11."""
    assert MAX_READ_BYTES + 1_000 < MAX_TOOL_RESULT_CHARS


# ── a clip must announce its own size ────────────────────────────────────────

def test_a_whole_file_arrives_with_no_truncation_notice(box, tmp_path):
    f = tmp_path / "small.md"
    f.write_text("x" * 500)
    out, err = box.dispatch("read_file", {"path": str(f)})
    assert not err
    assert "TRUNCATED" not in out


def test_a_clipped_read_states_both_byte_counts_and_a_percentage(box, tmp_path):
    f = tmp_path / "big.md"
    total = MAX_READ_BYTES * 4
    f.write_text("x" * total)
    out, _ = box.dispatch("read_file", {"path": str(f)})
    assert "TRUNCATED" in out
    assert f"{MAX_READ_BYTES:,}" in out and f"{total:,}" in out
    assert "about 25%" in out  # the number is the point: 10% and 99% must differ


def test_the_notice_says_the_rest_is_not_below(box, tmp_path):
    """The 2026-08-11 failure was answering from a partial read without hedging.
    The notice has to be unambiguous that content is missing, not just short."""
    f = tmp_path / "big.md"
    f.write_text("x" * (MAX_READ_BYTES * 2))
    out, _ = box.dispatch("read_file", {"path": str(f)})
    assert "The rest is NOT below" in out
    assert "not seen" in out or "did not see" in out


def test_the_clip_lands_exactly_on_the_limit(box, tmp_path):
    f = tmp_path / "big.md"
    f.write_text("x" * (MAX_READ_BYTES * 2))
    out, _ = box.dispatch("read_file", {"path": str(f)})
    assert out.count("x") == MAX_READ_BYTES


# ── the alarm that was missing ───────────────────────────────────────────────

# Documents the decision spine shows agents actually reading whole, rather than
# grepping. Each must fit under the read ceiling; when one outgrows it, the agent
# silently starts reasoning from a fragment, so this test is the early warning.
# leads.yaml is deliberately absent — it is raw ore, read for sampling, and is
# expected to clip (the notice above is what makes that honest).
READ_WHOLE = [
    "docs/uzelhub-crew/NEWSROOM.md",      # carries `read: full` in its own front matter
    "ops/calendar.ics",                   # the to-do spine; outgrew the old ceiling 08-03
]


@pytest.mark.parametrize("rel", READ_WHOLE)
def test_documents_meant_to_be_read_whole_still_fit(rel):
    p = _REPO / rel
    if not p.exists():
        pytest.skip(f"{rel} not present on this box")
    size = p.stat().st_size
    assert size <= MAX_READ_BYTES, (
        f"{rel} is {size:,} bytes, past the {MAX_READ_BYTES:,}-byte read ceiling — "
        f"agents reading it now silently get the first {MAX_READ_BYTES * 100 // size}%. "
        f"Raise the ceiling, split the document, or give it a digest like the calendar's."
    )


def test_the_predictor_project_plan_still_fits():
    """Lives outside this repo, so it gets its own test rather than a repo-relative
    parametrize. 90KB on 2026-08-11 — the file that motivated the 40k -> 120k raise."""
    p = Path("/opt/predictor_ingest/docs/project-plan.md")
    if not p.exists():
        pytest.skip("predictor_ingest not present on this box")
    assert p.stat().st_size <= MAX_READ_BYTES
