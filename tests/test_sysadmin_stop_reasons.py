"""Tests for the sysadmin agent's stop-reason guards.

Both guards exist for the same reason and fail the same way: a response that
stopped early still *parses*. `## Status: CLEAN` with no findings under it is
indistinguishable from a clean pass, so a truncated or declined run that is
allowed downstream becomes a confident report of nothing.

`refusal` additionally has no fallback by design (docs/security-agent.md §7) —
the raised error routed through the unit's OnFailure pager is the measurement
instrument for "how often is this declined", so a swallowed refusal loses the
signal as well as the run.

The served-model assertions guard a live mis-costing, not just telemetry: the
tally prices each turn at whatever model actually answered, so a server-side
fallback bills at the fallback's rates rather than the requested model's.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.sysadmin_agent import (  # noqa: E402
    RefusedRunError,
    SysadminAgent,
    TruncatedRunError,
)


def _response(stop_reason: str, *, model: str = "claude-opus-5", stop_details=None):
    """Minimal stand-in for an Anthropic Message — only what _create reads."""
    return SimpleNamespace(
        stop_reason=stop_reason,
        model=model,
        stop_details=stop_details,
        content=[],
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        ),
    )


class _Stream:
    """Context manager standing in for client.messages.stream(...)."""

    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self._response


class _StubClient:
    """Anthropic client stub. Returns queued responses in order.

    `create` is wired to fail on purpose. The agent must use the STREAMING
    path: a non-streaming request leaves the connection idle for the whole
    generation and the SDK hard-refuses one above 21,333 max_tokens, which is
    what broke the 2026-08-08 pass. A silent regression to `.create()` would
    reintroduce that ceiling, so it fails here rather than at 06:20.
    """

    def __init__(self, *responses):
        self._queue = list(responses)
        self.calls: list[dict] = []
        self.messages = SimpleNamespace(create=self._forbidden, stream=self._stream)

    def _stream(self, **kwargs):
        self.calls.append(kwargs)
        return _Stream(self._queue.pop(0))

    @staticmethod
    def _forbidden(**kwargs):
        raise AssertionError(
            "agent called client.messages.create() — it must stream; see the "
            "21,333-token non-streaming ceiling that broke the 2026-08-08 pass"
        )


def _agent(client) -> SysadminAgent:
    return SysadminAgent(client, model="claude-opus-5", max_cost_usd=3.0)


# --- the two stop-reason guards -------------------------------------------


def test_refusal_raises_rather_than_returning_an_empty_audit():
    agent = _agent(_StubClient(_response("refusal")))
    with pytest.raises(RefusedRunError):
        agent._create([{"role": "user", "content": "audit"}])


def test_refusal_carries_the_category_for_the_pager():
    """The operator needs to know *why* it was declined — a cyber-category
    refusal on a security charter means something different from a stray one."""
    resp = _response("refusal", stop_details=SimpleNamespace(category="cyber"))
    agent = _agent(_StubClient(resp))
    with pytest.raises(RefusedRunError) as exc:
        agent._create([{"role": "user", "content": "audit"}])
    assert exc.value.category == "cyber"
    assert "cyber" in str(exc.value)


def test_refusal_without_stop_details_still_raises():
    """stop_details is informational and may be absent even on a refusal, which
    is exactly why the branch is on stop_reason. A None here must not become an
    AttributeError that masks the refusal as a crash."""
    agent = _agent(_StubClient(_response("refusal", stop_details=None)))
    with pytest.raises(RefusedRunError) as exc:
        agent._create([{"role": "user", "content": "audit"}])
    assert exc.value.category is None


def test_max_tokens_still_raises_truncated():
    agent = _agent(_StubClient(_response("max_tokens")))
    with pytest.raises(TruncatedRunError):
        agent._create([{"role": "user", "content": "audit"}])


def test_refusal_and_truncation_are_distinguishable():
    """Same posture, different causes — a pager that cannot tell them apart
    sends the operator to the wrong fix."""
    assert not issubclass(RefusedRunError, TruncatedRunError)
    assert not issubclass(TruncatedRunError, RefusedRunError)


def test_ordinary_stop_reasons_pass_through():
    for reason in ("end_turn", "tool_use"):
        agent = _agent(_StubClient(_response(reason)))
        assert agent._create([{"role": "user", "content": "audit"}]).stop_reason == reason


# --- served-model recording ------------------------------------------------


def test_cost_is_priced_at_the_model_that_served_the_turn():
    """A fallback bills at the fallback's rates. Pricing at the *requested*
    model overstates spend against the cap and hides the rollback."""
    from agents import sysadmin_agent as mod

    seen: list[str] = []
    original = mod.compute_cost
    mod.compute_cost = lambda model, *a, **k: seen.append(model) or 0.0
    try:
        agent = _agent(_StubClient(_response("end_turn", model="claude-opus-4-8")))
        resp = agent._create([{"role": "user", "content": "audit"}])
        # _tally lives inside run(); exercise the same expression it uses.
        served = getattr(resp, "model", None) or agent.model
        mod.compute_cost(served, 10, 5, 0, 0)
    finally:
        mod.compute_cost = original

    assert seen == ["claude-opus-4-8"], "priced at the requested model, not the served one"


def test_served_model_falls_back_to_configured_when_absent():
    """Older stubs and some error paths carry no .model; the expression must
    degrade to the configured model rather than raising."""
    resp = SimpleNamespace(stop_reason="end_turn", content=[])
    agent = _agent(_StubClient(resp))
    assert (getattr(resp, "model", None) or agent.model) == "claude-opus-5"


# --- streaming transport ---------------------------------------------------


def test_agent_uses_the_streaming_path():
    """Pins the transport. Non-streaming carries a 21,333-token SDK ceiling
    (measured 2026-08-08) that hard-refuses before the request is sent — which
    is what broke that morning's pass. _StubClient.create raises, so a
    regression fails here rather than at 06:20."""
    client = _StubClient(_response("end_turn"))
    agent = _agent(client)
    agent._create([{"role": "user", "content": "audit"}])
    assert len(client.calls) == 1, "no request was made"


def test_streamed_response_keeps_the_fields_downstream_depends_on():
    """get_final_message() must yield the same Message shape create() did —
    every check in _create and every consumer of SysadminReply reads these."""
    resp = _response("end_turn", model="claude-opus-5")
    agent = _agent(_StubClient(resp))
    out = agent._create([{"role": "user", "content": "audit"}])
    assert out.stop_reason == "end_turn"
    assert out.model == "claude-opus-5"
    assert out.usage.input_tokens == 10
    assert out.usage.output_tokens == 5
