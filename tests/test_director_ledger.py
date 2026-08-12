"""Tests for the Director's ledger — write exception 2, granted 2026-08-11.

The ledger is the Director's memory across runs: notes its past self left for the
run it is in now. Two properties have to hold or it becomes a liability rather
than a memory. It must be **append-only** — a memory that can rewrite its own
history is worse than none, since nothing downstream can trust a citation. And it
must be **injected, not discovered** — the whole failure it exists to fix was the
Director rediscovering the same thing six mornings running because nothing
carried forward.

    .venv/bin/python -m pytest tests/test_director_ledger.py -q
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pipelines.director.project_state import LEDGER_BUDGET, ledger
from pipelines.director.tools import TOOL_DEFS, default_toolbox

_REPO = Path(__file__).resolve().parents[1]
_HELPER = _REPO / "ops" / "ledger-append"
_LEDGER = _REPO / "docs" / "director" / "director-ledger.md"

HEADER = "# Director — Ledger\n\nintro prose\n\n---\n\n## 2026-01-01 — First\n\nbody\n"


@pytest.fixture
def scratch(tmp_path):
    p = tmp_path / "director-ledger.md"
    p.write_text(HEADER, encoding="utf-8")
    return p


def _append(target, title, body, author="director", extra=()):
    return subprocess.run(
        [str(_HELPER), "--author", author, "--ledger", str(target), "--title", title, *extra],
        input=body, capture_output=True, text=True, timeout=15,
    )


# ── the helper generalised past the sysadmin ─────────────────────────────────

def test_director_is_an_accepted_author():
    """It was operator/sysadmin only until the Director got a ledger."""
    out = subprocess.run([str(_HELPER), "--help"], capture_output=True, text=True).stdout
    assert "director" in out


def test_a_non_sysadmin_ledger_is_accepted(scratch):
    """The sentinel used to be the sysadmin ledger's exact title, which would
    have refused this file outright."""
    assert _append(scratch, "A finding", "with receipts").returncode == 0


def test_a_file_that_is_not_a_ledger_is_still_refused(tmp_path):
    """Generalising the sentinel must not turn it into 'any markdown file'."""
    stray = tmp_path / "notes.md"
    stray.write_text("# Some Document\n\n---\n\nbody\n")
    r = _append(stray, "Nope", "body")
    assert r.returncode != 0 and "does not look like a ledger" in (r.stdout + r.stderr)


# ── append-only is the load-bearing property ─────────────────────────────────

def test_prior_entries_are_byte_identical_after_a_write(scratch):
    before = scratch.read_text()
    assert _append(scratch, "Second finding", "more receipts").returncode == 0
    after = scratch.read_text()
    assert before[:before.index("---") + 3] == after[:after.index("---") + 3]  # header
    assert "## 2026-01-01 — First\n\nbody" in after                            # old entry
    assert len(after) > len(before)


def test_the_newest_entry_lands_at_the_top(scratch):
    """Read tools return a bounded prefix, so append-at-bottom silently loses the
    newest entries first — the inversion of what a memory needs."""
    _append(scratch, "Newest", "body")
    text = scratch.read_text()
    assert text.index("## 2026-") < text.index("## 2026-01-01 — First")


def test_a_duplicate_title_on_the_same_day_is_refused(scratch):
    assert _append(scratch, "Same", "body").returncode == 0
    assert _append(scratch, "Same", "different body").returncode != 0


def test_a_body_with_a_top_level_heading_is_refused(scratch):
    """An entry that opens its own '#' section would break the file's structure."""
    assert _append(scratch, "Bad shape", "# Heading\n\nbody").returncode != 0


def test_an_empty_body_is_refused(scratch):
    assert _append(scratch, "No body", "   ").returncode != 0


# ── the Director's own verb ──────────────────────────────────────────────────

def test_the_toolbox_exposes_ledger_append():
    names = [t["name"] for t in TOOL_DEFS]
    assert "ledger_append" in names


def test_the_model_cannot_choose_the_author_or_the_target():
    """Identity and target file are the toolbox's to set, never the model's —
    same division as the calendar verbs."""
    spec = next(t for t in TOOL_DEFS if t["name"] == "ledger_append")
    props = spec["input_schema"]["properties"]
    assert set(props) == {"title", "body"}
    assert spec["input_schema"]["additionalProperties"] is False


def test_the_verb_refuses_a_half_written_entry():
    box = default_toolbox()
    out, err = box.dispatch("ledger_append", {"title": "no body", "body": ""})
    assert err and "needs both" in out


# ── injected, not discovered ─────────────────────────────────────────────────

def test_the_real_ledger_loads_and_is_within_budget():
    text = ledger()
    assert text.startswith("# Director — Ledger")
    assert len(text) < LEDGER_BUDGET, "ledger is due a compaction per its read contract"


def test_a_missing_ledger_degrades_quietly(monkeypatch):
    """No ledger yet is a normal state — it must not take a turn down."""
    import pipelines.director.project_state as ps
    monkeypatch.setattr(ps, "_REPO_DOCS", Path("/nonexistent"))
    assert ps.ledger() == ""


def test_an_oversized_ledger_says_so_rather_than_clipping_silently(monkeypatch, tmp_path):
    """The 2026-08-03 calendar lesson, applied to its own memory."""
    import pipelines.director.project_state as ps
    big = tmp_path / "director-ledger.md"
    big.write_text("# Director — Ledger\n" + "x" * (LEDGER_BUDGET + 5_000))
    monkeypatch.setattr(ps, "_REPO_DOCS", tmp_path)
    out = ps.ledger()
    assert "past its" in out and "Propose a compaction" in out
