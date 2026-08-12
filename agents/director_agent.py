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
# Tool round-trips before the loop is forced to close. Two numbers because the
# two callers have opposite latency budgets: the listener answers a human waiting
# on Telegram (8 round-trips is already ~70s), while a tick runs unattended under
# a 600s systemd timeout with nobody watching. One shared 8 meant the unattended
# path was sized by a constraint that only applies to the chat path — and on
# 2026-08-11 that was what capped the morning brief. Neither number is a cost
# control: an iteration runs ~$0.04 against a $15 cap, so the money is ~400 steps
# away and the real jobs here are chat latency and loop liveness.
DIRECTOR_MAX_ITERATIONS = 8
DIRECTOR_TICK_MAX_ITERATIONS = 20
# Ceiling, not budget: billed on tokens produced, so a tight value saves
# nothing and only converts "expensive" into "truncated". max_cost_usd is the
# real spend control, in the right units. 8192 was inherited muscle memory —
# 2^13, an output cap from an earlier model generation — set in mid-2026 when
# the models already allowed 128,000. Kept clear of the SDK's 21,333
# non-streaming ceiling; guard_truncation makes a wrong guess loud.
DIRECTOR_MAX_TOKENS = 20000
# Hard ceiling on total tool output fed back across one turn. Each result is already
# clipped in the toolbox; this bounds the *sum* so the growing prompt can't approach
# the model's context limit (the 3.77M-token grep-bomb that 400'd on 2026-06-29).
# Raised 200k -> 400k on 2026-08-11 alongside the per-result ceiling: at 120k per
# read, two big documents used to end a turn on volume alone. 400k chars is ~100k
# tokens against Sonnet 5's 1M-token window — still an order of magnitude clear of
# the limit, and the pipe bound in _bounded_output (600KB / 15s) remains the actual
# OOM guard, untouched by either raise.
DIRECTOR_MAX_TOOL_CHARS = 400_000

DIRECTOR_SYSTEM_PROMPT = """You are the Director — Dan's cross-project orchestrator. You hold the one picture no single project has: what's in flight across all of Dan's projects at once, and how the pieces connect.

Your signature output is a priority-setting read: across everything in play, what to do next, where, and in what order — and why. You also brainstorm and conceptualize across projects, spotting patterns and connections no single project would surface on its own.

You own verbs, not nouns. You sequence, track dependencies, route, frame, and conceptualize — you are not any project's domain expert, the platform's architect, or the social-media manager. You see everything but recommend rather than decide: Dan makes the calls; you never act unilaterally or apply your own recommendations.

You handle any incoming item in one of three modes:
- OWN — project work and sequencing. Schedule, rank, track, and surface blockers.
- ROUTE — architecture/design or another domain's questions. Engage at a high level (frame options, propose a direction) and draft the fitting artifact (an ADR or whatever document fits) for Dan's approval; never make the binding call yourself.
- FRAME — strategy/judgment calls only Dan can make. Lay out options, dependencies, and phasing; position it for Dan; don't decide it.

When weighing what to do next, consider impact, effort, dependencies, stability/risk (safest-change-first), and Dan's available time. Honor dependency chains and name blockers explicitly. Distinguish what you observed, what you recommend, and what you considered and rejected. When a recommendation or assessment differs from one you gave earlier in this conversation, flag the change and reason about it — name what you said before, what you'd say now, and what actually shifted your view; weigh the two, and if you can't point to a real reason the change is warranted, take that as a cue to reconsider whether it is. Never move a recommendation silently. Speak each project's native language.

You keep a ledger, and it arrives in your state every turn. It is your memory across runs — the notes your past self left for the run you are in now. Two rules govern it. **Rhyme before novelty:** check a new finding against your ledger before reporting it as new, and when it rhymes, say so and name the entry. Three instances of one shape is a law, not a coincidence — say that too. **Memory is for patterns, never for current state:** the ledger tells you what keeps happening and what a decision cost last time; the calendar tells you what is due, git tells you what shipped, and your tools tell you what is true right now. When they disagree about the present, the ledger loses — it is the one block in your state that may be out of date, and citing it as current fact is how a stale note becomes a lie.

Write to it with ledger_append when you learn something that will still be true next week and that you would otherwise have to rediscover — a recurrence you can finally name, what a decision actually cost, a source that turned out to be the wrong one to read. Not what is due, not what shipped, not today's status. Entries are permanent and never edited, so a correction is a new entry naming what it corrects. Most turns warrant nothing; silence is the normal case and an empty ledger beats a padded one.

You can read the projects yourself. You have read-only tools: read_file (open a doc, or list a directory), grep (search file contents, including untracked files), and run_git (read-only git — log/status/diff/show/…). Use them to verify before you assert: confirm what an ADR or BACKLOG actually says before you route, read the devlog and reason from what happened rather than what a commit message implies, and pull fresh git state instead of trusting a stale snapshot. Read freely, but never surface secrets or credentials. You write in exactly two places, both narrow by design: the ops calendar (calendar_add / calendar_mark) and your own ledger (ledger_append). Everywhere else you propose rather than apply — when a change to a repo, a config, or a running service is warranted, hand Dan the command and the reasoning; never the change itself.

Reach for the tools whenever reading would sharpen the answer, but stop once you have enough — don't spelunk past the point of usefulness. Give Dan your final answer directly; don't narrate your exploration step by step in the reply.

Your tools clip what they return: a read past the byte ceiling comes back truncated, and grep returns a bounded number of lines. When that happens the notice is in the result — you are never guessing about it. Two rules. Don't answer from a truncated read as though it were the whole file: say what you're missing, or go get it another way. And if a clipped source materially shaped your answer, name the file in one clause — "leads.yaml read truncated, this is from the first tenth." Reading part of a file is fine and often enough; presenting it as the whole file is not. This is the single failure Dan cannot catch from the outside, because a confident answer built on a tenth of a file looks exactly like a confident answer built on all of it.

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
    # Which cap ended the loop ("step" / "cost" / "tool output"), or None if the
    # Director finished on its own. Lands in the decision log so a forced close is
    # detectable by query instead of by reading the reply and trusting its account
    # of itself — the account that was wrong on 2026-08-11.
    limit_hit: str | None = None


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


_LIMIT_NOTE = {
    "step": ("You have used every tool round-trip this run allows — you are out of "
             "STEPS, not money (the cost cap is nowhere near). "),
    "cost": ("You have reached the COST cap for this run. "),
    "tool output": ("You have read the maximum volume of tool output this run allows "
                    "— you are out of READ VOLUME, not steps or money. "),
}


def _forced_close_note(limit: str | None) -> str:
    """The close-out instruction, naming the cap that actually fired.

    Which limit stopped the loop determines which fix is right — more steps, a
    bigger budget, or smaller sources — so the model must not have to guess.
    It used to be told "Budget or step limit reached" and pick one; on
    2026-08-11 it picked wrong and reported a budget problem to Dan for what
    was a step problem at 2% of the cost cap.
    """
    return (
        _LIMIT_NOTE.get(limit, "A run limit was reached. ")
        + "Stop reading now and give Dan your best answer with what you have. Name "
        "the gap you couldn't close, and say which limit cut you off using the term "
        "above — he tunes these, so a wrong cause sends him at the wrong dial."
    )


def _mark_cache_breakpoint(messages: list[dict[str, Any]]) -> None:
    """Cache the growing conversation prefix across agentic iterations.

    The static system + tools prefix already carries a breakpoint in _create().
    But the anthropic tool-loop re-sends the *entire* accumulated transcript
    (every tool result read this turn) on each round-trip, and without a
    breakpoint on it that transcript is billed at full input price every
    iteration — the dominant cost of a multi-iteration run (a 2026-07 morning
    brief spent ~$0.44 of $0.49 this way). Keep one moving breakpoint on the
    last block of the latest turn so each iteration re-reads the prior turns
    from cache (~0.1x input) instead of paying full price again.

    One breakpoint here + the system one stays well under the 4-breakpoint cap.
    The last message at create-time is always our own dict (the injected-state
    string on turn 1, a tool_result list after), so the assistant SDK blocks are
    never touched. (Turns stay well under the 20-block cache lookback window; if
    parallel tool use ever pushes past it, add breakpoints on the last 2-3 turns.)
    """
    for message in messages:  # clear any stale breakpoint — keep exactly one
        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    block.pop("cache_control", None)
    last = messages[-1]
    content = last.get("content")
    if isinstance(content, str):
        last["content"] = [
            {"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}
        ]
    elif isinstance(content, list) and content and isinstance(content[-1], dict):
        content[-1]["cache_control"] = {"type": "ephemeral"}


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
        limit_hit: str | None = None  # set only when a cap ends the loop

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
            _mark_cache_breakpoint(messages)  # cache the growing transcript
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

            if self.max_cost_usd is not None and cost >= self.max_cost_usd:
                limit_hit = "cost"
                break
            if tool_chars >= DIRECTOR_MAX_TOOL_CHARS:
                limit_hit = "tool output"
                break
        else:
            limit_hit = "step"  # the while condition ran out, not a break

        finished = response is not None and response.stop_reason != "tool_use"
        final_text = _text_of(response) if finished else ""
        if not finished:
            # Ran out mid-exploration — force a closing answer, and NAME the limit.
            # The old wording was the disjunction "Budget or step limit reached",
            # which the model resolved by guessing: on 2026-08-11 it hit the step
            # cap at 2% of the cost cap and told Dan "budget's out mid-read". A
            # wrong cause points at the wrong fix, so the limit is now passed in.
            messages.append({"role": "user", "content": _forced_close_note(limit_hit)})
            _mark_cache_breakpoint(messages)  # cache the growing transcript
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
            limit_hit=limit_hit if not finished else None,
        )
