"""One page in, the right ore's prompt out, and the guard on both ways.

`triage()` used to branch twice: the transcript path built its call, ran the
truncation guard and returned early, and the git path did the same thing again
a few lines down. Two copies of one rule is how a fix lands on one source and
misses the other — which is not hypothetical here. a861925's message said it
had guarded "the transcript path too" when it had guarded only `triage()`, and
the miss cost a $0.43 silent run before anyone saw it.

Consolidated to one guard after the branch on 2026-09-07. These two tests pin
what the consolidation must not break: the prompt that goes with each source,
and the guard that both sources pass through.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import agents.scout_agent as scout  # noqa: E402


class _Client:
    """Records what was sent and answers with whatever the test needs."""

    def __init__(self, text: str = '{"jewels": []}', stop_reason: str = "end_turn"):
        self.sent: list[dict] = []
        self._text = text
        self._stop = stop_reason
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.sent.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self._text)],
            usage=SimpleNamespace(input_tokens=10, output_tokens=5),
            stop_reason=self._stop,
        )


def _agent(client) -> scout.ScoutAgent:
    return scout.ScoutAgent(
        client,
        walk_model="walk-model",
        synthesis_model="synth-model",
        synthesis_fallback="fallback-model",
        toolbox=object(),  # triage never dispatches a tool
    )


def test_each_source_gets_its_own_prompt_and_header():
    """The ore's stance lives in its prompt: a session log records a problem
    being fought, a commit records what was decided. Crossing the wires would
    mine the right page under the wrong instructions and cite the wrong key."""
    client = _Client()
    agent = _agent(client)

    agent.triage("rows", source="transcript")
    agent.triage("commits", source="git")

    assert client.sent[0]["system"] is scout.SCOUT_TRIAGE_PROMPT
    assert client.sent[0]["messages"][0]["content"].startswith("Transcript page:")
    assert client.sent[1]["system"] is scout.SCOUT_GIT_TRIAGE_PROMPT
    assert client.sent[1]["messages"][0]["content"].startswith("Commit page:")


def test_both_sources_reach_the_truncation_guard(monkeypatch):
    """The consolidation's whole point. A source that skipped the guard would
    log "0 jewels", persist nothing, pay full price and move on."""
    seen: list[str] = []
    monkeypatch.setattr(
        scout,
        "_keep_evidence_if_empty",
        lambda call, source, messages=None: seen.append(source),
    )
    agent = _agent(_Client(text="", stop_reason="max_tokens"))

    for source in ("transcript", "git"):
        with pytest.raises(scout.TriageTruncated):
            agent.triage("page", source=source)

    # Captured before the raise, both times — the raise must not lose the
    # evidence for the call it is raising about.
    assert seen == ["transcript", "git"]


def test_an_unknown_source_refuses_rather_than_guessing_a_prompt():
    with pytest.raises(ValueError):
        _agent(_Client()).triage("page", source="calendar")
