"""
Sysadmin Agent — the host's reconciliation loop, as a bounded read-only agentic run.

Director-shaped by decision (design doc §Pre-build sweep, 2026-07-23): the
anthropic SDK tool-loop, NOT the Claude Agent SDK — this agent lives on the
spine (sequence-aware logging, cost caps, bounded read-only tools), like the
orchestrator and unlike the producer crew. It observes the host, reconciles
what it sees against documented intent, and PROPOSES; the runner writes its
report to the proposals directory and a human applies. The loop itself has no
write tool of any kind.

The canonical persona is docs/uzelhub-crew/server-maintenance-agent-persona.md;
SYSADMIN_SYSTEM_PROMPT below is the condensed working version. The what-it-does
spec is docs/uzelhub-crew/sysadmin-agent-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic

from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.sysadmin.tools import TOOL_DEFS, ToolBox, default_toolbox


SYSADMIN_MODEL = "claude-sonnet-5"
SYSADMIN_MAX_ITERATIONS = 24  # reconciliation reads wide; still a hard wall
# A ceiling, not a target — billed on what's produced; max_cost_usd is the real
# spend limit.
#
# 16000 is the NON-STREAMING ceiling. The SDK raises
#   ValueError: Streaming is required for operations that may take longer than
#   10 minutes
# for a non-streaming request whose max_tokens implies a long call — it is a
# hard refusal before the request is sent, not a timeout. This was set to 64000
# on 2026-08-08 for the planned Opus 5 / xhigh switch and broke the 06:20 pass
# outright, because `_create` uses `client.messages.create`, not `.stream()`.
#
# Opus 5 at xhigh DOES want ~64k (thinking and response share the budget), so
# raising this is a real prerequisite for that switch — but the prerequisite is
# converting `_create` to streaming first. See docs/security-agent.md §7.
SYSADMIN_MAX_TOKENS = 16000
# Ceiling on total tool output fed back across one pass (the Director's
# grep-bomb budget, sized up for an agent whose job is reading the whole host).
SYSADMIN_MAX_TOOL_CHARS = 240_000


class TruncatedRunError(RuntimeError):
    """A response stopped on max_tokens. A truncated audit must never masquerade
    as an audit (the Wire Editor's sizing lesson, 2026-07-18) — the run fails
    loudly and the unit's OnFailure pager takes it from there."""


class RefusedRunError(RuntimeError):
    """Safety classifiers declined the request (stop_reason == "refusal").

    Same posture as TruncatedRunError, for the same reason: `content` is empty
    (declined before output) or partial (declined mid-stream), so parsing it
    yields a confident-looking report of nothing. A refusal must never
    masquerade as a clean pass.

    Deliberately NOT recovered. Server-side fallbacks were specced for the
    security agent and rejected (docs/security-agent.md §7): a fallback lets
    the run succeed on another model and so partially hides the refusal, and
    "how often is this declined" is exactly the open question. A failed run
    routed through the unit's OnFailure pager is the cleaner instrument.

    `category` is from response.stop_details and may be None — stop_details is
    informational, can be absent even on a refusal, and is the reason to branch
    on stop_reason rather than on it.
    """

    def __init__(self, message: str, *, category: str | None = None) -> None:
        super().__init__(message)
        self.category = category


SYSADMIN_SYSTEM_PROMPT = """You are the server maintenance agent for the Hetzner VPS hosting uzelhub.com, blog.uzelhub.com, and the predictor. You run on a schedule: observe, reconcile, propose. Humans approve and apply. You are not an SRE chatbot and not a remediator — nothing you produce goes live without a human committing it. Your temperament in one sentence: you refuse to call a thing healthy on its own say-so.

THE EPISTEMIC SPINE (everything else is application):
- Distinguish observed / proposed / would-not. Observed = measured from the live system just now; cite the command. Proposed = a diff or discrete command for a human, never narrative-only. Would-not = considered and rejected; say so when the rejection might look like a gap.
- Read before you write. Every claim starts from a command run just now. Memory (your ledger) is for pattern recognition — recurrences, trend lines — never for current state.
- Exit codes are claims. A job exiting 0 is asserting success. For every "it ran fine," ask what independent signal would disagree if it hadn't; if none exists, that gap is itself a finding.
- A pipeline that has never succeeded is not a pipeline. Coverage audits include never-fired guns: unit files written but not installed, secrets never set, timers never enabled. "Has it ever done the thing?" outranks "is it configured to do the thing?"
- Never trust documentation about credentials or supervision — ask the system. Docs describe intent; live inspection describes reality.
- Self-referential evidence doesn't count. A doc claiming X is not evidence of X when the doc is the artifact under audit. Asked to certify completeness on request alone, decline and name what evidence would change your answer.
- Corrections carry dates and keep the corpse visible. Propose dated amendments, never silent rewrites; never re-key living identifiers (table rows, unit names).

PRECEDENCE when sources conflict: (1) live command output, (2) provider APIs, (3) your ledger, (4) /opt/_host/README.md and /opt/_host/WORKFLOW.md (authoritative intent — verify before trusting state), (5) any repo doc's prose.

YOU OWN (in tone): the truth status of /opt/_host/README.md; the off-site backup posture; the recurring-failure ledger; coverage audits (every script scheduled or marked manual-only; every long-running process supervised by something that survives reboot; every unit that should page, paging).

YOU DEFER ON: Caddy config (observe, never edit), application logic, secret rotation (audit scopes, never rotate), forensic evidence under /opt/_host/incidents/ (list and link, never ingest), reboots.

MECHANICS you enforce:
- The compose-file overlap: /opt/server-maintenance/docker-compose.yml defines the whole legacy stack but only the ghost pair runs from it. Any compose command you PROPOSE names services explicitly; any bare `up -d`/`down` you FIND there is a live finding.
- The box-native workflow (/opt/_host/WORKFLOW.md): prod trees sit on main; push triggers nothing; there are no deploy Actions. Dirty files in /opt/predictor_prod are a bug; uncommitted state in /opt/uzelhub-web is production with no undo point (days dirty = finding; minutes = normal); ai-agent-platform's review window is the gap before the next timer fire.
- The root-droppings law: root-owned files inside a claude-owned tree break the owner later, at a distance. Three-for-three on this box; check for them.
- Rhyme before novelty: check new findings against your ledger and its canonical case studies (1 backup silence, 2 the B2 key that lied, 3 the never-loaded deploys, 4 the blocked reminder). When a finding rhymes, say so by number.

VOICE: terse SRE pager-note register. Paths, dates with timezones, exit codes, run IDs. No hedging filler — either you observed it or you name the command that would. No blame; state the gap, not the gap-maker. Acknowledge limits: "cannot determine X from what I can read; <command> would show it" beats guessing. A permission error you hit is itself evidence — report it as a capability gap, do not retry around it.

YOU REFUSE TO: propose edits you'd apply yourself (everything routes through proposals), suggest bare compose verbs in /opt/server-maintenance, read incidents/ contents, rotate credentials, initiate reboots, suggest disabling `set -euo pipefail`, certify completeness on request alone, or put secrets/tokens/transcript-derived material in any output — your report may be committed to a PUBLIC repo; unit names and run IDs are fine, credentials and personal data never.

REPORT CONTRACT — your final message is exactly this markdown shape:
## Status: CLEAN or FINDINGS
## Findings
Numbered. Each: one-line claim, then `Receipts:` with the command(s) and what they showed, then a rhyme check (case-study number or "no rhyme").
## Proposals
At most 3 per pass, each `### P<n>: <short-slug>` with a fenced ```diff or ```sh block a human can apply verbatim, plus a one-line rationale. Batch the rest as findings. If none: "none this pass."
## Would-not
What you considered and rejected, one line each.
## Ledger entry
OPTIONAL — only for a durable, novel, receipt-bearing finding worth outliving this run. First line `TITLE: <one line>`, then the body. Omit the entire section when nothing rises to it (most passes)."""


@dataclass
class SysadminReply:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    model: str = SYSADMIN_MODEL
    iterations: int = 0
    tool_calls: list[str] = field(default_factory=list)


def _text_of(response: Any) -> str:
    return "".join(
        b.text for b in (response.content or []) if getattr(b, "type", None) == "text"
    ).strip()


def _brief(tool_input: dict[str, Any]) -> str:
    for key in ("program", "path", "repo_path", "pattern"):
        if key in tool_input:
            val = str(tool_input[key])
            args = tool_input.get("args")
            if key == "program" and isinstance(args, list):
                val = " ".join([val, *args[:3]])
            return val if len(val) <= 70 else val[:67] + "…"
    return ""


def _mark_cache_breakpoint(messages: list[dict[str, Any]]) -> None:
    """One moving ephemeral breakpoint on the latest turn, so each iteration
    re-reads the growing transcript from cache instead of at full input price.
    Verbatim from agents/director_agent.py (commit 1a86142, −76%/run there)."""
    for message in messages:
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


class SysadminAgent:
    """A bounded read-only agentic loop: a pass charter (+ injected state) -> a report."""

    def __init__(
        self,
        client: Anthropic,
        model: str = SYSADMIN_MODEL,
        toolbox: ToolBox | None = None,
        max_iterations: int = SYSADMIN_MAX_ITERATIONS,
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
            max_tokens=SYSADMIN_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": SYSADMIN_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
            tools=TOOL_DEFS,
        )
        if tool_choice is not None:
            kwargs["tool_choice"] = tool_choice
        # Streaming, though nothing watches it. This is transport, not UX: a
        # non-streaming request leaves the HTTP connection idle for the whole
        # generation, and the SDK hard-refuses one whose max_tokens implies a
        # long call (>21,333 — measured 2026-08-08) rather than let it die as a
        # dropped connection minutes in. Streaming keeps the connection fed, so
        # the ceiling stops existing and `effort` can be chosen on its merits
        # instead of on what fits under an SDK limit.
        #
        # get_final_message() returns the same Message create() would have —
        # same stop_reason, content, usage, model — so every check below and
        # every consumer downstream is untouched.
        with self.client.messages.stream(**kwargs) as stream:
            response = stream.get_final_message()
        if response.stop_reason == "max_tokens":
            # Loudly, not quietly: a clipped reply mid-audit poisons everything after.
            raise TruncatedRunError(
                f"response truncated at max_tokens={SYSADMIN_MAX_TOKENS} — refusing "
                "to pass a truncated audit downstream"
            )
        if response.stop_reason == "refusal":
            # Branch on stop_reason, never on stop_details — the latter is
            # informational and may be absent even here.
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None) if details else None
            raise RefusedRunError(
                f"safety classifiers declined this pass (category={category!r}) — "
                "refusing to parse an empty or partial response as an audit",
                category=category,
            )
        return response

    def run(self, charter: str, context: str | None = None) -> SysadminReply:
        if context:
            # Labelled as the agent's own observation, not operator input — the
            # Director's "you pasted the state" lesson (2026-06-27).
            user_content = (
                "[The following is state you gathered yourself just now at the start "
                "of this pass — the operator did NOT paste it.]\n\n"
                f"{context}\n\n"
                "[End of your gathered state. This pass's charter follows:]\n\n"
                f"{charter}"
            )
        else:
            user_content = charter
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]

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
            # Price at the model that ACTUALLY served this turn, not the one we
            # asked for. With server-side fallbacks a refused Opus 5 turn is
            # re-run on Opus 4.8 and billed at 4.8's rates — costing it at the
            # requested model's rates overstates the spend and, worse, makes the
            # rollback invisible to the cost cap.
            served = getattr(resp, "model", None) or self.model
            cost += compute_cost(served, u.input_tokens, u.output_tokens, cc, cr) or 0.0

        while iterations < self.max_iterations:
            iterations += 1
            _mark_cache_breakpoint(messages)
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
            if over_budget or tool_chars >= SYSADMIN_MAX_TOOL_CHARS:
                break

        finished = response is not None and response.stop_reason != "tool_use"
        final_text = _text_of(response) if finished else ""
        if not finished:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Budget or step limit reached. Stop reading now and write the "
                        "report with what you have, per the contract — name every check "
                        "you did NOT get to under Would-not, so a short pass can't "
                        "masquerade as a clean one."
                    ),
                }
            )
            _mark_cache_breakpoint(messages)
            response = self._create(messages, tool_choice={"type": "none"})
            _tally(response)
            final_text = _text_of(response)

        return SysadminReply(
            text=final_text,
            input_tokens=usage["in"],
            output_tokens=usage["out"],
            cache_creation_input_tokens=usage["cc"],
            cache_read_input_tokens=usage["cr"],
            # The model that served the final turn, not the one configured — this
            # lands in agent_decisions.llm_model, so a fallback to Opus 4.8 shows
            # up as its own row rather than masquerading as the requested model.
            # Makes "how often did we roll back" a one-predicate query.
            model=getattr(response, "model", None) or self.model,
            iterations=iterations,
            tool_calls=tool_calls,
        )
