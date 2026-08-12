"""Shared stop-reason guards for the crew.

A response that stopped early still *parses*. A truncated triage still has
verdicts in it; a truncated draft still reads like prose; `## Status: CLEAN`
with nothing under it is indistinguishable from a clean pass. So the failure is
not that the agent crashes — it is that the agent doesn't, and the half-answer
flows downstream wearing the shape of a whole one.

**This is not theoretical.** Queried 2026-08-12, `agent_decisions` holds two
runs that stopped on `max_tokens` at exactly 8,192 output tokens — one
`chief_shadow`, one `wire_triage`. Neither agent checked `stop_reason`, so both
truncated responses were parsed and used. Nobody noticed at the time.

The Wire Editor is the instructive one: it now runs at `max_tokens=64000` and
its clean passes reach ~54k output, so the ceiling was raised *after* it was
bitten — and the silent-failure hole underneath was left open. **Raising a
ceiling is not the same as noticing when you hit one.**

Two separate guards, deliberately not one:

- `guard_truncation` is unconditional. Nothing recovers from a clipped
  response; the run must fail loudly and let the unit's `OnFailure=` pager
  take it.
- `guard_refusal` is opt-in, because refusal is sometimes *recoverable*. The
  Writer retries once tool-less on its fallback model and that is correct
  behaviour — a shared guard that raised here would break it. Agents with no
  recovery path call it; agents with one handle refusal themselves.
"""
from __future__ import annotations

from typing import Any


class TruncatedRunError(RuntimeError):
    """A response stopped on `max_tokens`.

    A truncated audit must never masquerade as an audit (the Wire Editor's
    sizing lesson, 2026-07-18) — the run fails loudly and the unit's OnFailure
    pager takes it from there.
    """


class RefusedRunError(RuntimeError):
    """Safety classifiers declined the request (`stop_reason == "refusal"`).

    Same posture as TruncatedRunError, for the same reason: `content` is empty
    (declined before output) or partial (declined mid-stream), so parsing it
    yields a confident-looking report of nothing.

    `category` comes from `response.stop_details` and may be None —
    `stop_details` is informational, can be absent even on a refusal, and is
    exactly why the branch below is on `stop_reason` instead.
    """

    def __init__(self, message: str, *, category: str | None = None) -> None:
        super().__init__(message)
        self.category = category


def guard_truncation(response: Any, *, max_tokens: int, agent: str) -> None:
    """Raise if the response was clipped by the token ceiling.

    Call immediately after obtaining the message, before anything parses it.
    Unconditional by design: there is no sensible recovery from half an answer,
    and the alternative — passing it on — is the silent failure this exists to
    end.
    """
    if getattr(response, "stop_reason", None) == "max_tokens":
        raise TruncatedRunError(
            f"{agent}: response truncated at max_tokens={max_tokens} — refusing "
            "to pass a clipped response downstream. Raise the ceiling if this "
            "is routine (streaming lifts the SDK's non-streaming cap), but do "
            "not silence the guard: the ceiling and the noticing are separate."
        )


def guard_refusal(response: Any, *, agent: str) -> None:
    """Raise if safety classifiers declined the request.

    Opt-in — see the module docstring. Only for agents with no recovery path;
    an agent that retries on a fallback should handle `refusal` itself rather
    than call this.
    """
    if getattr(response, "stop_reason", None) == "refusal":
        # Branch on stop_reason, never on stop_details — the latter is
        # informational and may be absent even here.
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None) if details else None
        raise RefusedRunError(
            f"{agent}: safety classifiers declined this request "
            f"(category={category!r}) — refusing to parse an empty or partial "
            "response as a result",
            category=category,
        )
