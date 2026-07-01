"""
Director Agent — the cross-project orchestrator's reasoning, as an agentic loop.

The Director runs a bounded, read-only tool loop on the **anthropic SDK** — the
crew's own substrate, deliberately NOT the Claude Agent SDK — so every round-trip's
tokens and cost flow straight into the agent_decisions spine. It reads the box on
demand (read_file / grep / run_git, see pipelines/director/tools.py) to verify before
it ranks or routes. The loop is bounded by an iteration cap and an optional cost cap;
when it runs out of budget mid-exploration it is forced to give Dan its best answer.

The canonical persona is docs/director/director-persona.md (its [PROMPT] sections).
DIRECTOR_SYSTEM_PROMPT below is the condensed working version.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic

from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.director.tools import TOOL_DEFS, ToolBox, default_toolbox


DIRECTOR_MODEL = "claude-sonnet-5"
DIRECTOR_MAX_ITERATIONS = 8  # tool round-trips before the loop is forced to close
DIRECTOR_MAX_TOKENS = 8192
# Hard ceiling on total tool output fed back across one turn. Each result is already
# clipped in the toolbox; this bounds the *sum* so the growing prompt can't approach
# the model's context limit (the 3.77M-token grep-bomb that 400'd on 2026-06-29).
DIRECTOR_MAX_TOOL_CHARS = 200_000

DIRECTOR_SYSTEM_PROMPT = """You are the Director — Dan's cross-project orchestrator. You hold the one picture no single project has: what's in flight across all of Dan's projects at once, and how the pieces connect.

Your signature output is a priority-setting read: across everything in play, what to do next, where, and in what order — and why. You also brainstorm and conceptualize across projects, spotting patterns and connections no single project would surface on its own.

You own verbs, not nouns. You sequence, track dependencies, route, frame, and conceptualize — you are not any project's domain expert, the platform's architect, or the social-media manager. You see everything but recommend rather than decide: Dan makes the calls; you never act unilaterally or apply your own recommendations.

You handle any incoming item in one of three modes:
- OWN — project work and sequencing. Schedule, rank, track, and surface blockers.
- ROUTE — architecture/design or another domain's questions. Engage at a high level (frame options, propose a direction) and draft the fitting artifact (an ADR or whatever document fits) for Dan's approval; never make the binding call yourself.
- FRAME — strategy/judgment calls only Dan can make. Lay out options, dependencies, and phasing; position it for Dan; don't decide it.

When weighing what to do next, consider impact, effort, dependencies, stability/risk (safest-change-first), and Dan's available time. Honor dependency chains and name blockers explicitly. Distinguish what you observed, what you recommend, and what you considered and rejected. When a recommendation or assessment differs from one you gave earlier in this conversation, flag the change and reason about it — name what you said before, what you'd say now, and what actually shifted your view; weigh the two, and if you can't point to a real reason the change is warranted, take that as a cue to reconsider whether it is. Never move a recommendation silently. Speak each project's native language.

You can read the projects yourself. You have read-only tools: read_file (open a doc, or list a directory), grep (search file contents, including untracked files), and run_git (read-only git — log/status/diff/show/…). Use them to verify before you assert: confirm what an ADR or BACKLOG actually says before you route, read the devlog and reason from what happened rather than what a commit message implies, and pull fresh git state instead of trusting a stale snapshot. Read freely, but never surface secrets or credentials. You have no write tools by design — when a change is warranted, propose it for Dan to approve.

Reach for the tools whenever reading would sharpen the answer, but stop once you have enough — don't spelunk past the point of usefulness. Give Dan your final answer directly; don't narrate your exploration step by step in the reply.

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
    iterations: int = 0
    tool_calls: list[str] = field(default_factory=list)


def _text_of(response: Any) -> str:
    """Final answer = the text blocks only (skip thinking/tool_use blocks)."""
    return "".join(
        b.text for b in (response.content or []) if getattr(b, "type", None) == "text"
    ).strip()


def _brief(tool_input: dict[str, Any]) -> str:
    """A short tag for the decision-log trace, e.g. read_file(BACKLOG.md)."""
    for key in ("path", "project_path", "pattern"):
        if key in tool_input:
            val = str(tool_input[key])
            return val if len(val) <= 70 else val[:67] + "…"
    return ""


class DirectorAgent:
    """A bounded read-only agentic loop: a message (+ history + eyes) -> a reply."""

    def __init__(
        self,
        client: Anthropic,
        model: str = DIRECTOR_MODEL,
        toolbox: ToolBox | None = None,
        max_iterations: int = DIRECTOR_MAX_ITERATIONS,
        max_cost_usd: float | None = None,
    ) -> None:
        self.client = client
        self.model = model
        self.toolbox = toolbox if toolbox is not None else default_toolbox()
        self.max_iterations = max_iterations
        self.max_cost_usd = max_cost_usd

    def _create(self, messages: list[dict[str, Any]], tool_choice: Any | None = None):
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=DIRECTOR_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": DIRECTOR_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
            tools=TOOL_DEFS,  # always declared (stable prefix → cache-friendly)
        )
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        return self.client.messages.create(**kwargs)

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
                "the repos — Dan did NOT paste it. Treat it as your own fresh observation, "
                "and read deeper with your tools where it matters.]\n\n"
                f"{context}\n\n"
                "[End of your observation. Dan's message follows:]\n\n"
                f"{message}"
            )
        else:
            user_content = message
        messages: list[dict[str, Any]] = list(history or [])
        messages.append({"role": "user", "content": user_content})

        usage = {"in": 0, "out": 0, "cc": 0, "cr": 0}
        tool_calls: list[str] = []
        cost = 0.0
        tool_chars = 0
        iterations = 0
        response = None

        def _tally(resp: Any) -> None:
            nonlocal cost
            u = resp.usage
            cc = getattr(u, "cache_creation_input_tokens", 0) or 0
            cr = getattr(u, "cache_read_input_tokens", 0) or 0
            usage["in"] += u.input_tokens
            usage["out"] += u.output_tokens
            usage["cc"] += cc
            usage["cr"] += cr
            cost += compute_cost(self.model, u.input_tokens, u.output_tokens, cc, cr) or 0.0

        while iterations < self.max_iterations:
            iterations += 1
            response = self._create(messages)
            _tally(response)
            if response.stop_reason != "tool_use":
                break

            messages.append({"role": "assistant", "content": response.content})
            results: list[dict[str, Any]] = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                args = dict(block.input or {})
                out, is_err = self.toolbox.dispatch(block.name, args)
                tool_chars += len(out)
                tool_calls.append(
                    f"{block.name}({_brief(args)})" + (" !err" if is_err else "")
                )
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": out,
                        "is_error": is_err,
                    }
                )
            messages.append({"role": "user", "content": results})

            over_budget = self.max_cost_usd is not None and cost >= self.max_cost_usd
            if over_budget or tool_chars >= DIRECTOR_MAX_TOOL_CHARS:
                break  # budget/output spent — fall through to a forced close

        finished = response is not None and response.stop_reason != "tool_use"
        final_text = _text_of(response) if finished else ""
        if not finished:
            # Ran out of iterations or budget mid-exploration — force a closing answer.
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Budget or step limit reached. Stop reading now and give Dan your "
                        "best answer with what you have — name any gap you couldn't close."
                    ),
                }
            )
            response = self._create(messages, tool_choice={"type": "none"})
            _tally(response)
            final_text = _text_of(response)

        return DirectorReply(
            text=final_text,
            input_tokens=usage["in"],
            output_tokens=usage["out"],
            cache_creation_input_tokens=usage["cc"],
            cache_read_input_tokens=usage["cr"],
            model=self.model,
            iterations=iterations,
            tool_calls=tool_calls,
        )
