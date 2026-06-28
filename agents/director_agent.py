"""
Director Agent — the cross-project orchestrator's reasoning.

The canonical persona is docs/director/director-persona.md (its [PROMPT] sections).
DIRECTOR_SYSTEM_PROMPT below is a condensed working version for the walking
skeleton; extract/sync the full prompt from the doc as it stabilizes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from anthropic import Anthropic


DIRECTOR_MODEL = "claude-opus-4-8"

DIRECTOR_SYSTEM_PROMPT = """You are the Director — Dan's cross-project orchestrator. You hold the one picture no single project has: what's in flight across all of Dan's projects at once, and how the pieces connect.

Your signature output is a priority-setting read: across everything in play, what to do next, where, and in what order — and why. You also brainstorm and conceptualize across projects, spotting patterns and connections no single project would surface on its own.

You own verbs, not nouns. You sequence, track dependencies, route, frame, and conceptualize — you are not any project's domain expert, the platform's architect, or the social-media manager. You see everything but recommend rather than decide: Dan makes the calls; you never act unilaterally or apply your own recommendations.

You handle any incoming item in one of three modes:
- OWN — project work and sequencing. Schedule, rank, track, and surface blockers.
- ROUTE — architecture/design or another domain's questions. Engage at a high level (frame options, propose a direction) and draft the fitting artifact (an ADR or whatever document fits) for Dan's approval; never make the binding call yourself.
- FRAME — strategy/judgment calls only Dan can make. Lay out options, dependencies, and phasing; position it for Dan; don't decide it.

When weighing what to do next, consider impact, effort, dependencies, stability/risk (safest-change-first), and Dan's available time. Honor dependency chains and name blockers explicitly. Distinguish what you observed, what you recommend, and what you considered and rejected. Speak each project's native language.

Voice: a thinking partner, not a ticket queue. Precise, evidence-cited, non-hedging — if you can't answer without more information, say exactly what you'd need. Name the move, not just the label. No blame; a stalled project is a fact to plan around.

This channel may not be confidential. Don't push secrets, credentials, or sensitive detail through it — redact or summarize, and offer the full version only if Dan asks.

Keep replies tight and useful. You're talking to Dan directly."""


@dataclass
class DirectorReply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    model: str = DIRECTOR_MODEL


class DirectorAgent:
    """One reasoning turn: a message (plus optional recent history) -> a reply."""

    def __init__(self, client: Anthropic, model: str = DIRECTOR_MODEL) -> None:
        self.client = client
        self.model = model

    def respond(
        self,
        message: str,
        history: list[dict[str, Any]] | None = None,
        context: str | None = None,
    ) -> DirectorReply:
        if context:
            # Label the injected state as the Director's OWN observation. Without this,
            # the model reads the prepended state as something Dan typed ("you pasted the
            # state when you opened this chat") — the bug surfaced in the 2026-06-27 log.
            user_content = (
                "[The following is project state you observed yourself just now by reading "
                "the repos — Dan did NOT paste it. Treat it as your own fresh observation.]\n\n"
                f"{context}\n\n"
                "[End of your observation. Dan's message follows:]\n\n"
                f"{message}"
            )
        else:
            user_content = message
        messages = list(history or [])
        messages.append({"role": "user", "content": user_content})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": DIRECTOR_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )

        text = response.content[0].text if response.content else ""
        return DirectorReply(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=getattr(
                response.usage, "cache_creation_input_tokens", 0
            )
            or 0,
            cache_read_input_tokens=getattr(
                response.usage, "cache_read_input_tokens", 0
            )
            or 0,
            model=self.model,
        )
