"""Tests for the gate's diff-awareness — the hook blocks what a commit ADDS.

The suppression logic is exercised through check() with injected readers, so
no git plumbing and no secret-shaped fixtures: findings come from the
employer-gate term detector primed with a word that exists nowhere else.

    .venv/bin/python -m pytest tests/test_redaction_gate.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "redaction_gate", _REPO / "tools" / "redaction_gate.py")
gate = importlib.util.module_from_spec(_spec)
sys.modules["redaction_gate"] = gate
_spec.loader.exec_module(gate)

TERMS = gate.term_pattern(["flurbomatic"])
DIRTY = "the flurbomatic ships in Q3\n"
CLEAN = "the widget ships in Q3\n"


def _run(staged: dict, head: dict, allow: set[str] = frozenset()):
    return gate.check(
        list(staged), staged.get, TERMS, set(allow), baseline=head.get)


def test_finding_already_in_head_is_suppressed_not_blocking():
    hits, suppressed = _run({"a.md": DIRTY}, {"a.md": DIRTY})
    assert hits == []
    assert suppressed == 1


def test_new_finding_in_existing_file_blocks():
    hits, suppressed = _run({"a.md": DIRTY}, {"a.md": CLEAN})
    assert len(hits) == 1
    assert suppressed == 0


def test_new_file_gets_no_baseline_and_blocks():
    hits, suppressed = _run({"new.md": DIRTY}, {})
    assert len(hits) == 1
    assert suppressed == 0


def test_suppression_is_per_file_not_repo_wide():
    # The key existing in HEAD's copy of a DIFFERENT file excuses nothing.
    hits, suppressed = _run({"b.md": DIRTY}, {"a.md": DIRTY})
    assert len(hits) == 1
    assert suppressed == 0


def test_allow_verdict_still_applies_before_baseline():
    hits, suppressed = _run(
        {"new.md": DIRTY}, {}, allow={"employer-gate:flurbomatic"})
    assert hits == []
    assert suppressed == 0


def test_no_baseline_means_full_strength():
    # The --all / explicit-path audits pass baseline=None and report everything.
    hits, suppressed = gate.check(
        ["a.md"], {"a.md": DIRTY}.get, TERMS, set(), baseline=None)
    assert len(hits) == 1
    assert suppressed == 0
