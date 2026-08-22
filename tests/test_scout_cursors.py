"""The two read positions, and the pass that drives them.

The cursor file is the Scout's only durable claim about what it has read. A
bug here does not crash — it silently rewinds coverage, or silently stops
advancing, and the first symptom is noticing months later that a stretch of
ore was never walked. So the state-file handling and the pass composition get
tested rather than eyeballed.

The composition test stubs `_walk_stage` itself and asserts on HOW it was
called: which position each leg starts from, what budget it gets, and whether
the backfill leg runs at all. That is the part the retool added and the part
with arithmetic in it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.scout import run as run_mod  # noqa: E402
from pipelines.scout.config import ScoutConfig  # noqa: E402
from pipelines.scout.walk import load_cursors, save_cursors  # noqa: E402


# --- the state file ------------------------------------------------------------


def test_missing_file_starts_both_at_zero(tmp_path):
    assert load_cursors(tmp_path) == {"forward": 0, "backfill": 0}


def test_legacy_single_cursor_reads_as_forward(tmp_path):
    """The pre-retool shape. Misreading it as backfill=418876 would mark the
    whole archive already re-mined; misreading it as forward=0 would re-walk
    the entire corpus as if it were new. Both are silent."""
    (tmp_path / "cursor.json").write_text(json.dumps({"seq": 418876}))
    assert load_cursors(tmp_path) == {"forward": 418876, "backfill": 0}


def test_writing_one_position_preserves_the_other(tmp_path):
    """save_cursors must never blind-write the file. A pass advances forward
    every page; if that also wrote whatever backfill it read at start, an
    interleaved reclaim would have its progress stamped over."""
    (tmp_path / "cursor.json").write_text(json.dumps({"seq": 418876}))

    save_cursors(tmp_path, backfill=1200)
    assert load_cursors(tmp_path) == {"forward": 418876, "backfill": 1200}

    save_cursors(tmp_path, forward=419000)
    assert load_cursors(tmp_path) == {"forward": 419000, "backfill": 1200}

    save_cursors(tmp_path)  # neither: a no-op, not a wipe
    assert load_cursors(tmp_path) == {"forward": 419000, "backfill": 1200}


def test_state_file_stays_hand_readable(tmp_path):
    """It lives outside the database so a human can read and edit it. If it
    ever stops being obvious JSON, that property is gone."""
    save_cursors(tmp_path, forward=5, backfill=2)
    assert json.loads((tmp_path / "cursor.json").read_text()) == {
        "forward": 5,
        "backfill": 2,
    }


# --- the retired knob ----------------------------------------------------------


def test_retired_walk_pages_is_honoured_not_ignored(monkeypatch):
    """Someone who tuned SCOUT_WALK_PAGES deliberately should get what they
    asked for. A dead env var that still looks live is diagnosed months late."""
    monkeypatch.setenv("SCOUT_WALK_PAGES", "3")
    monkeypatch.setenv("SCOUT_PAGE_ROWS", "150")
    assert ScoutConfig.from_env().pass_row_budget == 450


def test_new_knob_wins_over_the_retired_one(monkeypatch):
    monkeypatch.setenv("SCOUT_WALK_PAGES", "3")
    monkeypatch.setenv("SCOUT_PASS_ROW_BUDGET", "150")
    assert ScoutConfig.from_env().pass_row_budget == 150


def test_default_plate_is_150_not_450(monkeypatch):
    monkeypatch.delenv("SCOUT_WALK_PAGES", raising=False)
    monkeypatch.delenv("SCOUT_PASS_ROW_BUDGET", raising=False)
    assert ScoutConfig.from_env().pass_row_budget == 150


# --- the pass composition ------------------------------------------------------


def _config(tmp_path, budget=150) -> ScoutConfig:
    return ScoutConfig(
        postgres_dsn="", anthropic_api_key="k", walk_model="m", synthesis_model="m",
        synthesis_fallback="m", page_rows=150, pass_row_budget=budget, roam_iterations=1,
        max_cost_usd=99.0, logs_dir=Path("/tmp"), codex_logs_dir=Path("/tmp"),
        state_dir=tmp_path, leads_path=tmp_path / "leads.yaml",
    )


@pytest.fixture
def pass_harness(monkeypatch):
    """Everything but the composition is stubbed. `legs` records how each call
    to _walk_stage was parameterised — that is what is under test."""
    legs: list[dict] = []

    def fake_walk_stage(conn, agent, config, log_manager, run_id, *, cursor,
                        row_budget, summary, dry_run, cursor_key, cost_cap,
                        stop_at=None):
        legs.append({"cursor": cursor, "budget": row_budget,
                     "key": cursor_key, "stop_at": stop_at})
        # Behave like a walk that consumed its whole budget.
        summary["rows"] += row_budget
        summary["pages"] += 1
        return [], 0.0, cursor + row_budget

    monkeypatch.setattr(run_mod, "_walk_stage", fake_walk_stage)
    monkeypatch.setattr(run_mod, "_synthesis_stage", lambda *a, **k: 0.0)
    monkeypatch.setattr(run_mod, "_agent", lambda c: object())
    monkeypatch.setattr(run_mod.psycopg, "connect", lambda dsn: _FakeConn())
    monkeypatch.setattr(run_mod, "DecisionWriter", lambda conn: None)
    monkeypatch.setattr(run_mod, "SequenceAwareLogManager", lambda db_writer: _FakeLog())
    monkeypatch.setattr(run_mod, "create_run", lambda conn, name: "run-1")
    monkeypatch.setattr(run_mod, "complete_run", lambda *a, **k: None)
    return legs


class _FakeConn:
    def close(self):
        pass


class _FakeLog:
    def task_sequence(self, **k):
        import contextlib

        return contextlib.nullcontext()


def test_fresh_ore_has_first_claim_and_backfill_takes_the_remainder(pass_harness, tmp_path, monkeypatch):
    legs = pass_harness
    # Forward is far ahead, backfill at the start: there IS history to re-mine.
    save_cursors(tmp_path, forward=1000, backfill=0)
    # Fresh ore yields only 40 rows, leaving 110 of the 150-row plate spare.
    def forward_short(conn, agent, config, log_manager, run_id, *, cursor, row_budget,
                      summary, dry_run, cursor_key, cost_cap, stop_at=None):
        legs.append({"cursor": cursor, "budget": row_budget,
                     "key": cursor_key, "stop_at": stop_at})
        taken = 40 if cursor_key == "forward" else row_budget
        summary["rows"] += taken
        summary["pages"] += 1
        return [], 0.0, cursor + taken

    monkeypatch.setattr(run_mod, "_walk_stage", forward_short)
    summary = run_mod.run_pass(_config(tmp_path))

    assert [l["key"] for l in legs] == ["forward", "backfill"]
    assert legs[0]["cursor"] == 1000 and legs[0]["budget"] == 150
    assert legs[1]["cursor"] == 0, "backfill starts from its own position"
    assert legs[1]["budget"] == 110, "backfill gets only what fresh ore left"
    assert legs[1]["stop_at"] == 1000, "and stops where forward stood"
    assert summary["backfill_rows"] == 110


def test_a_busy_day_leaves_backfill_nothing(pass_harness, tmp_path):
    """Fresh ore filling the plate must not push the pass over budget by
    adding backfill on top — that would rebuild the 450-row plate by degrees."""
    legs = pass_harness
    save_cursors(tmp_path, forward=1000, backfill=0)
    summary = run_mod.run_pass(_config(tmp_path))
    assert [l["key"] for l in legs] == ["forward"]
    assert summary["rows"] == 150
    assert "backfill_rows" not in summary


def test_backfill_stops_once_it_has_caught_up(pass_harness, tmp_path, monkeypatch):
    """Caught up means the corpus has been re-mined once. Continuing would
    re-bill the whole archive on a loop."""
    legs = pass_harness

    def forward_short(conn, agent, config, log_manager, run_id, *, cursor, row_budget,
                      summary, dry_run, cursor_key, cost_cap, stop_at=None):
        legs.append({"key": cursor_key})
        summary["rows"] += 10
        return [], 0.0, cursor + 10

    monkeypatch.setattr(run_mod, "_walk_stage", forward_short)
    save_cursors(tmp_path, forward=500, backfill=500)  # level
    run_mod.run_pass(_config(tmp_path))
    assert [l["key"] for l in legs] == ["forward"], "no backfill leg once level"
