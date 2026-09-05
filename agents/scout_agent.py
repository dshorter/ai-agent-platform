"""
Scout Agent — the newsroom's prospector, as two stages with opposite needs.

NEWSROOM §Model tiers: the Scout is not one model call. The WALK (triage over
big swaths of transcript — high token volume, low IQ demand) runs on the cheap
tier, inheriting the marketer's Haiku-extraction split. The SYNTHESIS (the
"link 16 things because maybe" leap — low volume, maximum IQ) runs on the
premium tier, env-var'd, Fable 5 by plan. Nothing filters the Scout's missing
leads, so the synthesis model sets the ceiling on what stories ever exist.

Synthesis has HANDS: a bounded read-only roam (the Director's ToolBox —
read_file / grep / run_git — plus read_transcript over the ingested ore).
"Where do we go next" is a judgment call, so it lives on the premium seat;
Haiku is never asked to be curious — during the walk the cursor answers
"where next" mechanically. The tool-call trace lands in the spine, so which
sources each model *chooses* is an observable, not a vibe (the foraging half
of the Fable-vs-Sonnet A/B).

Both prompts hold the pineapple rule: aperture never narrows. Triage includes
when unsure; synthesis errs reckless; neither ever sees an Editor verdict.
The roam is free — a catalog of sources, no rotation, no quotas.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic

from agents.director_agent import _brief, _mark_cache_breakpoint
from pipelines.director.tools import MAX_TOOL_RESULT_CHARS, TOOL_DEFS, ToolBox, default_toolbox


# Deliberately NOT raised. Triage emits a short structured verdict per item;
# if it ever wants more than this, the output shape is wrong and stopping is
# correct. Here the ceiling is a sanity assertion, not a budget — which is
# only defensible because the output shape is known. The open-ended
# generators below get headroom instead.
SCOUT_TRIAGE_MAX_TOKENS = 4096
# Ceiling, not budget: billed on tokens produced, so a tight value saves
# nothing and only converts "expensive" into "truncated". max_cost_usd is the
# real spend control, in the right units. 8192 was inherited muscle memory —
# 2^13, an output cap from an earlier model generation — set in mid-2026 when
# the models already allowed 128,000. Kept clear of the SDK's 21,333
# non-streaming ceiling; guard_truncation makes a wrong guess loud.
#
# Tightest case on the box: synthesis runs on Fable 5, where thinking is
# ALWAYS on and shares this budget — so 8192 was funding the reasoning and
# the answer from one pot, on the step NEWSROOM.md calls the creative
# ceiling of the whole newsroom. Streaming this stage is the real fix.
SCOUT_SYNTHESIS_MAX_TOKENS = 20000
# Hard ceiling on total roam tool output across one synthesis (same guard the
# Director's loop carries against a context blowout).
SCOUT_MAX_TOOL_CHARS = 120_000
_TRANSCRIPT_MAX_ROWS = 80
_TRANSCRIPT_ROW_CLIP = 1500

# The roam borrows the Director's read-only hands (scoped roots, secret-file
# refusal, output bounding — all inherited), plus one Scout-native tool.
_ROAM_TOOL_NAMES = {"read_file", "grep", "run_git"}
_READ_TRANSCRIPT_DEF: dict[str, Any] = {
    "name": "read_transcript",
    "description": (
        "Read a range of ingested session-log rows (the Scout's ore) by seq — "
        "the numbers your jewels reference. Returns session/turn/role, the raw "
        "text (clipped), and any scratchpad arc-notes you left on prior walks. "
        "Use it to pull a thread a jewel points at."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "from_seq": {"type": "integer", "description": "First seq (inclusive)."},
            "to_seq": {"type": "integer", "description": f"Last seq (inclusive; max {_TRANSCRIPT_MAX_ROWS} rows per call)."},
        },
        "required": ["from_seq", "to_seq"],
        "additionalProperties": False,
    },
}


SCOUT_TRIAGE_PROMPT = """You are the Scout's walker — the cheap, wide-aperture triage stage of the uzelhub newsroom. You are reading one bounded page of Claude Code session transcripts: the human-AI collaboration that builds this platform ("the box"). The box narrates its own work; you mine the narration.

Mine for JEWELS — the durable material: named principles, corrections and reversals, reframes, decisions-with-reasons, aha-moments. NOT the play-by-play of which command ran. The richest material lives at the seams — human correcting model, one thread explaining another, an idea from days ago resurfacing.

Aperture rules (absolute):
- When unsure, include. A downstream editor filters; you never self-censor.
- You have no taste and want none. Never judge what "deserves" publishing — only note what is durable, surprising, or connective.

Output STRICT JSON, nothing else:
{"jewels": [{"seq": <int>, "kind": "principle|correction|reframe|decision|aha", "note": "<one tight sentence>"}],
 "scratchpad": [{"seq": <int>, "note": "<free-form arc breadcrumb, e.g. 'connects to the backup saga'>"}],
 "map_notes": ["<navigation observation: where rich material lives, which sources run rich — never story verdicts>"]}

seq values must come from the [seq=N] tags in the input. Keep notes short; the full text stays in the database."""


SCOUT_GIT_TRIAGE_PROMPT = """You are the Scout's walker — the cheap, wide-aperture triage stage of the uzelhub newsroom's prospector. You are reading one bounded page of COMMIT MESSAGES from the repositories that build this platform ("the box"). The box narrates its own work; you mine the narration.

This ore has a different register from the session logs, and that difference is the point. A session log records a problem WHILE IT IS BEING FOUGHT — partial, present tense, no resolution. A commit message records what was DECIDED and WHY, written afterwards, once it was known. You are mining the resolved account.

Mine for JEWELS — the durable material: named principles, corrections and reversals, reframes, decisions-with-reasons, aha-moments. NOT the play-by-play of which files changed. The richest material lives at the seams — a commit that reverses an earlier one, a message that explains a decision taken somewhere else, one change that touches two concerns at once, a rationale that outlives the code it shipped with.

Aperture rules (absolute):
- When unsure, include. A downstream editor filters; you never self-censor.
- You have no taste and want none. Never judge what "deserves" publishing — only note what is durable, surprising, or connective.

Output STRICT JSON, nothing else:
{"jewels": [{"ref": "<repo@sha>", "kind": "principle|correction|reframe|decision|aha", "note": "<one tight sentence>"}],
 "map_notes": ["<navigation observation: where rich material lives, which repos run rich — never story verdicts>"]}

Copy the value INSIDE the brackets exactly — `[ref=repo@sha]` means the ref is `repo@sha`, with the repo qualifier and nothing else. Do NOT append the commit date; it is outside the bracket because it is not part of the ref. A ref you were not shown, or one carrying anything extra, is dropped and the jewel is lost. Keep notes short; the full message stays in git."""


SCOUT_SYNTHESIS_PROMPT = """You are the Scout's synthesis leap — the premium stage of the uzelhub newsroom's prospector. Over triaged transcript jewels, cross-agent decision sequences, and your own navigation map, surface STORY LEADS: the platform narrating its own building, curated into pitches an editor can route.

You may INVESTIGATE before pitching. These sources exist on the box; where you go is entirely your call — no rotation, no quotas, and ignoring all of them is legitimate too:
- read_transcript — the ingested session-log ore, by seq (your jewels cite seqs; your own scratchpad arc-notes ride along).
- read_file / grep — the repos and docs: design docs (NEWSROOM, personas), the sysadmin ledger (docs/uzelhub-crew/sysadmin-ledger.md), the ops calendar (ops/calendar.ics), the marketing survey (uzelhub-web/marketing/promotion-survey.yaml), devlogs.
- run_git — read-only git across the registered projects (log/show/blame — when a story turns on when-and-why).
Your tool budget is small; spend it pulling threads, not surveying. When you have enough, stop and pitch.

Generate WIDE. Bold many-way connections are welcome — the best stories are the ones no pattern predicted. False positives are cheap (an editor spikes them); missed leads are invisible and unrecoverable. Err reckless.

Weighting: a lead whose evidence spans multiple agents deserves extra weight (stories live at the seams between agents) — but span never disqualifies a lone-actor story; keep surfacing those too.

Dedup: skip only a lead whose pitch is essentially identical to one in the already-pitched list. Never generalize that list into "avoid this kind of story."

REDACTION (absolute): these transcripts contain credentials, keys, internal paths, personal data. Never reproduce secret material in a pitch — point to it (session id, turns, sequence id, file) and paraphrase the story around it.

Registers: ticker (terse verb line), newsletter (weekly digest item), note (durable field note — self-awareness first, war story second), blog (narrative retelling).

Your FINAL message must be STRICT JSON, nothing else:
{"leads": [{"slug": "<kebab-case>", "pitch": "<2-4 sentences>", "why_now": "<one sentence>",
            "sources": ["<pointer, e.g. 'session 37e71c90 turns 210-260' or 'agent_decisions sequence <uuid>'>"],
            "register": "ticker|newsletter|note|blog", "agent_span": <int, 1 if single-actor>}]}"""


@dataclass
class ScoutCall:
    """One stage's result + usage, shaped for the agent_decisions spine."""
    data: dict
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    stop_reason: str | None = None
    fallback_used: bool = False
    iterations: int = 1
    tool_calls: list[str] = field(default_factory=list)  # the foraging trace
    raw_text: str = field(default="", repr=False)
    # Reasoning summary when the caller asks for `display: summarized`; empty
    # at every seat that leaves thinking display at the model's default.
    reasoning: str = field(default="", repr=False)


class TriageTruncated(RuntimeError):
    """A triage page hit the output ceiling, so its JSON is incomplete."""


def _guard_truncation(call: "ScoutCall", source: str) -> None:
    """Make a truncated page LOUD. It was silent, and that is the whole bug.

    `_parse_json` returns `{}` for an incomplete object, so a page that blew the
    output ceiling was indistinguishable from a page with nothing in it: the
    walk logged "0 jewels", persisted nothing, paid full price, and moved on.
    Found 2026-09-05 on the first live git walk — 150 commits, `max_tokens`,
    13,508 characters of perfectly good JSON thrown away without a word.

    Truncation is always total here, never partial: an unterminated object
    parses to nothing at all, so there is no salvageable half-page to continue
    with. Raising is therefore right — a walk persists per page, so everything
    already mined is safe, and stopping beats burning the rest of the corpus
    producing zeroes.
    """
    if call.stop_reason == "max_tokens" and not call.data:
        raise TriageTruncated(
            f"{source} triage hit the {SCOUT_TRIAGE_MAX_TOKENS}-token output "
            f"ceiling and its JSON is unparseable ({len(call.raw_text):,} chars "
            f"discarded). The PAGE is too big for this ore, not the ceiling too "
            f"small — size the page by how many jewels it will yield, not by "
            f"how much text it holds."
        )


def _parse_json(text: str) -> dict:
    """Tolerate a code fence or stray prose around the JSON object."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _text_of(resp: Any) -> str:
    return "".join(
        b.text for b in (resp.content or []) if getattr(b, "type", None) == "text"
    ).strip()


class ScoutAgent:
    def __init__(
        self,
        client: Anthropic,
        walk_model: str,
        synthesis_model: str,
        synthesis_fallback: str,
        roam_iterations: int = 6,
        toolbox: ToolBox | None = None,
    ) -> None:
        self.client = client
        self.walk_model = walk_model
        self.synthesis_model = synthesis_model
        self.synthesis_fallback = synthesis_fallback
        self.roam_iterations = roam_iterations
        self.toolbox = toolbox if toolbox is not None else default_toolbox()
        self.roam_tools = [d for d in TOOL_DEFS if d["name"] in _ROAM_TOOL_NAMES] + [
            _READ_TRANSCRIPT_DEF
        ]

    # --- plain single call (triage + refusal fallback) -----------------------
    def _call(self, model: str, system: str, user: str, max_tokens: int) -> ScoutCall:
        resp = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        call = ScoutCall(data=_parse_json(_text_of(resp)), model=model, raw_text=_text_of(resp))
        self._tally(call, resp)
        call.stop_reason = resp.stop_reason
        return call

    @staticmethod
    def _tally(call: ScoutCall, resp: Any) -> None:
        u = resp.usage
        call.input_tokens += u.input_tokens
        call.output_tokens += u.output_tokens
        call.cache_creation_input_tokens += getattr(u, "cache_creation_input_tokens", 0) or 0
        call.cache_read_input_tokens += getattr(u, "cache_read_input_tokens", 0) or 0

    def triage(self, page_text: str, source: str = "transcript") -> ScoutCall:
        """Mine one bounded page. `source` picks the ore's own prompt.

        The APERTURE RULES are identical across sources and must stay that way
        — "when unsure, include" and "you have no taste" are doctrine, not
        per-source tuning. What varies is the ore's register and the citation
        key: transcripts cite `seq` from `[seq=N]` tags, everything else cites
        `ref` from `[ref=...]` tags, which is the anchor `resolve_anchor`
        validates now that the foreign key is gone for five of six sources.
        """
        if source == "transcript":
            call = self._call(
                self.walk_model,
                SCOUT_TRIAGE_PROMPT,
                f"Transcript page:\n\n{page_text}",
                SCOUT_TRIAGE_MAX_TOKENS,
            )
            _guard_truncation(call, source)
            return call
        if source == "git":
            call = self._call(
                self.walk_model,
                SCOUT_GIT_TRIAGE_PROMPT,
                f"Commit page:\n\n{page_text}",
                SCOUT_TRIAGE_MAX_TOKENS,
            )
        else:
            raise ValueError(f"no triage prompt for source_type {source!r}")
        _guard_truncation(call, source)
        return call

    # --- the ore tool ---------------------------------------------------------
    @staticmethod
    def _read_transcript(conn, args: dict[str, Any]) -> tuple[str, bool]:
        try:
            a, b = int(args.get("from_seq")), int(args.get("to_seq"))
        except (TypeError, ValueError):
            return ("read_transcript needs integer from_seq/to_seq.", True)
        b = min(b, a + _TRANSCRIPT_MAX_ROWS - 1)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT seq, session_id, turn, role, turn_type,
                       LEFT(text, %s), scratchpad
                FROM scout_session_log
                WHERE seq BETWEEN %s AND %s
                ORDER BY seq
                """,
                (_TRANSCRIPT_ROW_CLIP, a, b),
            )
            rows = cur.fetchall()
        if not rows:
            return (f"(no rows in seq {a}-{b})", False)
        out = []
        for seq, sid, turn, role, ttype, text, pad in rows:
            head = f"[seq={seq} session={sid[:8]} turn={turn} {role}/{ttype}]"
            if pad:
                head += f"\n  (scratchpad: {pad})"
            out.append(f"{head}\n{text}")
        return ("\n\n".join(out)[:MAX_TOOL_RESULT_CHARS], False)

    # --- the leap, with hands -------------------------------------------------
    def synthesize(self, context: dict[str, Any], conn=None) -> ScoutCall:
        """Bounded agentic roam + the pitch. On stop_reason=refusal at any
        point, retry once as a plain (tool-less) call on the fallback model
        (NEWSROOM §Model tiers caveat — story-prospecting shouldn't trip the
        classifier, but wire the handling anyway)."""
        user = (
            "Jewels from this pass's transcript walk (seqs are read_transcript coordinates):\n"
            f"{json.dumps(context.get('jewels', []), indent=1)}\n\n"
            "Cross-agent decision sequences (agent_span = distinct agents touched; "
            "a weight, never a filter):\n"
            f"{json.dumps(context.get('sequences', []), indent=1)}\n\n"
            "Your navigation map (most recent notes):\n"
            f"{context.get('map', '(empty — first pass)')}\n\n"
            "Already-pitched (dedup ONLY — skip near-identical pitches, infer nothing else):\n"
            f"{json.dumps(context.get('pitched', []), indent=1)}\n\n"
            "Investigate if it helps, then surface your leads."
        )
        call = ScoutCall(data={}, model=self.synthesis_model)
        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        tool_chars = 0
        response = None

        def _create(tool_choice: Any | None = None):
            kwargs: dict[str, Any] = dict(
                model=self.synthesis_model,
                max_tokens=SCOUT_SYNTHESIS_MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": SCOUT_SYNTHESIS_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
                tools=self.roam_tools,
            )
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
            return self.client.messages.create(**kwargs)

        while call.iterations <= self.roam_iterations:
            _mark_cache_breakpoint(messages)  # re-read prior roam turns from cache
            response = _create()
            self._tally(call, response)
            if response.stop_reason == "refusal":
                fb = self._call(
                    self.synthesis_fallback, SCOUT_SYNTHESIS_PROMPT, user, SCOUT_SYNTHESIS_MAX_TOKENS
                )
                fb.fallback_used = True
                fb.tool_calls = call.tool_calls
                return fb
            if response.stop_reason != "tool_use":
                break
            call.iterations += 1
            messages.append({"role": "assistant", "content": response.content})
            results: list[dict[str, Any]] = []
            for block in response.content:
                if getattr(block, "type", None) != "tool_use":
                    continue
                args = dict(block.input or {})
                if block.name == "read_transcript":
                    if conn is None:
                        out, is_err = ("transcript store not available this run.", True)
                    else:
                        out, is_err = self._read_transcript(conn, args)
                    tag = f"read_transcript({args.get('from_seq')}-{args.get('to_seq')})"
                else:
                    out, is_err = self.toolbox.dispatch(block.name, args)
                    tag = f"{block.name}({_brief(args)})"
                tool_chars += len(out)
                call.tool_calls.append(tag + (" !err" if is_err else ""))
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": out,
                        "is_error": is_err,
                    }
                )
            messages.append({"role": "user", "content": results})
            if tool_chars >= SCOUT_MAX_TOOL_CHARS:
                break  # roam budget spent — force the pitch

        finished = response is not None and response.stop_reason != "tool_use"
        if not finished:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Roam budget reached. Stop investigating and output your leads "
                        "now — strict JSON only."
                    ),
                }
            )
            _mark_cache_breakpoint(messages)
            response = _create(tool_choice={"type": "none"})
            self._tally(call, response)

        call.raw_text = _text_of(response)
        call.data = _parse_json(call.raw_text)
        call.stop_reason = response.stop_reason
        return call
