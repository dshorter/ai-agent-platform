"""Tests for the shared stop-reason guards.

These exist because the failure they prevent already happened. Queried
2026-08-12, `agent_decisions` holds two runs that stopped on `max_tokens` at
exactly 8,192 output tokens — one `chief_shadow`, one `wire_triage`. Neither
agent checked `stop_reason`, so both clipped responses were parsed and used as
though complete, and nobody noticed at the time.

The shape of the bug is that nothing crashes: a truncated triage still contains
verdicts, a truncated draft still reads like prose. So the guard's whole job is
to convert a silent half-answer into a loud stop.

Two guards, not one — and the split is the load-bearing design decision:

  * truncation is unconditional (nothing recovers from half an answer)
  * refusal is opt-in, because the Writer *does* recover from it by retrying
    tool-less on its fallback model. A shared guard that raised on refusal
    would break behaviour that is working correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.stop_guards import (  # noqa: E402
    RefusedRunError,
    TruncatedRunError,
    guard_refusal,
    guard_truncation,
)


def _resp(stop_reason, *, stop_details=None):
    return SimpleNamespace(stop_reason=stop_reason, stop_details=stop_details)


# --- truncation: unconditional ---------------------------------------------


def test_truncation_raises():
    with pytest.raises(TruncatedRunError):
        guard_truncation(_resp("max_tokens"), max_tokens=8192, agent="wire_editor")


def test_truncation_message_names_the_agent_and_the_ceiling():
    """A pager note has to say which agent and which limit, or the operator
    starts from zero at 06:20."""
    with pytest.raises(TruncatedRunError) as exc:
        guard_truncation(_resp("max_tokens"), max_tokens=8192, agent="writer")
    assert "writer" in str(exc.value)
    assert "8192" in str(exc.value)


def test_truncation_passes_ordinary_stop_reasons():
    for reason in ("end_turn", "tool_use", "stop_sequence"):
        guard_truncation(_resp(reason), max_tokens=8192, agent="x")  # must not raise


def test_truncation_ignores_refusal():
    """Separation of concerns: an agent wiring only truncation must not start
    raising on refusal as a side effect — that would silently break the
    Writer's fallback retry."""
    guard_truncation(_resp("refusal"), max_tokens=8192, agent="writer")


def test_truncation_tolerates_a_response_without_stop_reason():
    """Some error paths and older stubs carry no stop_reason; a missing
    attribute must not become an AttributeError that masks the real problem."""
    guard_truncation(SimpleNamespace(), max_tokens=8192, agent="x")


# --- refusal: opt-in --------------------------------------------------------


def test_refusal_raises_and_carries_the_category():
    resp = _resp("refusal", stop_details=SimpleNamespace(category="cyber"))
    with pytest.raises(RefusedRunError) as exc:
        guard_refusal(resp, agent="security_audit")
    assert exc.value.category == "cyber"
    assert "security_audit" in str(exc.value)


def test_refusal_without_stop_details_still_raises():
    """stop_details is informational and may be absent even on a refusal —
    which is exactly why the branch is on stop_reason."""
    with pytest.raises(RefusedRunError) as exc:
        guard_refusal(_resp("refusal", stop_details=None), agent="x")
    assert exc.value.category is None


def test_refusal_ignores_truncation():
    guard_refusal(_resp("max_tokens"), agent="x")


def test_the_two_errors_are_distinguishable():
    """Same posture, different fixes. A handler that cannot tell them apart
    sends the operator down the wrong path."""
    assert not issubclass(RefusedRunError, TruncatedRunError)
    assert not issubclass(TruncatedRunError, RefusedRunError)


# --- the agents are actually wired -----------------------------------------


def test_every_bitten_agent_now_guards():
    """Pins the wiring itself. Both of these had a recorded max_tokens run and
    no guard; a refactor that drops the call would restore the silent failure
    without failing any behavioural test."""
    for module, sites in (("agents/wire_editor_agent.py", 1),
                          ("agents/writer_agent.py", 2),
                          ("agents/sysadmin_agent.py", 1)):
        src = (Path(__file__).resolve().parent.parent / module).read_text()
        assert src.count("guard_truncation(") >= sites, f"{module} lost its guard"


def test_writer_keeps_its_own_refusal_recovery():
    """The Writer must NOT use guard_refusal — it retries on a fallback model,
    and raising instead would turn a recoverable case into a lost run."""
    src = (Path(__file__).resolve().parent.parent / "agents/writer_agent.py").read_text()
    # `guard_refusal(` — the CALL. The bare name appears in a comment there
    # explaining precisely why it is not used, and an earlier version of this
    # test tripped on its own explanation.
    assert "guard_refusal(" not in src, "writer must not raise on refusal; it recovers"
    assert 'stop_reason == "refusal"' in src, "the recovery path itself is gone"
