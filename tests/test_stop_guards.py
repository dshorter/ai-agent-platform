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


# --- ceilings stay under the non-streaming cap -----------------------------


NON_STREAMING_CAP = 21_333  # measured by binary search against the SDK, 2026-08-08


def test_non_streaming_agents_stay_under_the_sdk_ceiling():
    """The SDK hard-refuses a non-streaming request above this — before the
    request is sent, so it is a startup failure, not a timeout. That is what
    broke sysadmin-daily on 2026-08-08. Any agent raised past the cap must
    convert to streaming in the same change."""
    import agents.director_agent as director
    import agents.scout_agent as scout
    import agents.writer_agent as writer

    for name, value in (
        ("writer", writer.WRITER_MAX_TOKENS),
        ("director", director.DIRECTOR_MAX_TOKENS),
        ("scout triage", scout.SCOUT_TRIAGE_MAX_TOKENS),
    ):
        assert value <= NON_STREAMING_CAP, (
            f"{name} at {value:,} exceeds the non-streaming ceiling — it must "
            f"stream (client.messages.stream) or drop below {NON_STREAMING_CAP:,}"
        )


def test_streaming_agents_may_exceed_it():
    """The converse: agents that stream are not bound by the cap, and the wire
    editor at 64,000 is the proof the exemption is real rather than theoretical."""
    import agents.wire_editor_agent as wire

    assert wire.WIRE_MAX_TOKENS > NON_STREAMING_CAP
    assert "messages.stream" in (
        Path(__file__).resolve().parent.parent / "agents/wire_editor_agent.py"
    ).read_text(), "wire editor exceeds the cap but no longer streams"


def test_scout_synthesis_streams_because_it_exceeds_the_cap():
    """Scout synthesis moved from the non-streaming list to this one on
    2026-09-06, which is the entire content of the change: the old 20,000 was
    not a considered budget, it was the largest number that fit under the cap,
    and reasoning shares that pot. Assert BOTH halves — a ceiling above the cap
    with no stream call is the startup failure this file exists to prevent."""
    import agents.scout_agent as scout

    assert scout.SCOUT_SYNTHESIS_MAX_TOKENS > NON_STREAMING_CAP
    source = (
        Path(__file__).resolve().parent.parent / "agents/scout_agent.py"
    ).read_text()
    assert "messages.stream" in source, (
        "scout synthesis exceeds the cap but no longer streams"
    )


def test_scout_never_asks_for_a_separate_reasoning_budget():
    """budget_tokens is a 400 on the synthesis seat (Sonnet 5) — the second of
    the two fixes the code offered itself for a month, and the one that was
    never available. Reaching for it again is the regression worth catching in
    a test rather than in a paid run."""
    import ast

    tree = ast.parse(
        (Path(__file__).resolve().parent.parent / "agents/scout_agent.py").read_text()
    )
    # Grep is wrong here: the guard's error message says the word "budget_tokens"
    # on purpose, to warn the next reader off it. Only a real dict key or kwarg
    # reaches the API, so that is what gets asserted.
    sent = [
        node.lineno
        for node in ast.walk(tree)
        if (isinstance(node, ast.keyword) and node.arg == "budget_tokens")
        or (
            isinstance(node, ast.Dict)
            and any(
                isinstance(k, ast.Constant) and k.value == "budget_tokens"
                for k in node.keys
            )
        )
    ]
    assert not sent, f"budget_tokens is a 400 on this seat; sent at lines {sent}"
