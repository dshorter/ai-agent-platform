"""Tests for the run caps — which one fired, and what the Director is told.

The 2026-08-11 morning brief hit the step cap at 2% of the cost cap and opened
with "Budget's out mid-read". The loop had told it "Budget or step limit
reached" and it resolved the disjunction by guessing. A wrong cause is worse
than no cause: it sends Dan to tune the dial that wasn't the problem. So the
close-out names the cap, and the cap's name lands in the decision log where it
can't be re-narrated.

    .venv/bin/python -m pytest tests/test_director_limits.py -q
"""
from __future__ import annotations

import pytest

from agents.director_agent import (
    DIRECTOR_MAX_ITERATIONS,
    DIRECTOR_TICK_MAX_ITERATIONS,
    _forced_close_note,
)


# ── the close-out names the cap ──────────────────────────────────────────────

def test_step_limit_says_steps_and_rules_out_money():
    note = _forced_close_note("step")
    assert "STEPS" in note
    assert "not money" in note  # the exact confusion that happened


def test_cost_limit_says_cost():
    assert "COST" in _forced_close_note("cost")


def test_tool_output_limit_says_read_volume():
    note = _forced_close_note("tool output")
    assert "READ VOLUME" in note
    assert "not steps or money" in note


@pytest.mark.parametrize("limit", ["step", "cost", "tool output", None])
def test_every_close_out_still_asks_for_the_gap(limit):
    """The graceful-degradation half worked on 2026-08-11 and is not being
    changed — only the label was wrong. Guard the part that was right."""
    note = _forced_close_note(limit)
    assert "gap you couldn't close" in note
    assert "best answer with what you have" in note


def test_unknown_limit_degrades_without_naming_a_wrong_one():
    """Better to say nothing specific than to assert the wrong cap."""
    note = _forced_close_note(None)
    for wrong in ("STEPS", "COST", "READ VOLUME"):
        assert wrong not in note


# ── the two caps are actually different ──────────────────────────────────────

def test_the_tick_gets_a_larger_step_budget_than_the_chat():
    """Unattended vs. a human waiting on Telegram — different latency budgets,
    so a single shared constant was sizing the tick by the chat's constraint."""
    assert DIRECTOR_TICK_MAX_ITERATIONS > DIRECTOR_MAX_ITERATIONS


def test_the_tick_budget_stays_inside_its_systemd_timeout():
    """~9s per round-trip observed on 2026-08-11 (69.3s / 8). The unit allows
    600s, so the step budget must not be the thing that trips the wall clock."""
    assert DIRECTOR_TICK_MAX_ITERATIONS * 9 < 600
