"""
Writer Agent — the newsroom's rewrite desk, note leg first.

writer-persona.md is the identity; this is its runtime. The Writer takes a
CLAIMED lead (pitch, why-now, sources, register) and produces the register's
output — v1: a notes.json-shaped field-note entry. It has no voice of its own:
the voice bottle (voice/<profile>/samples + moves.md) rides in the system
prompt, and the samples carry the voice.

The roam is the Scout's kit pointed the opposite way — CONVERGENT: pull
exactly the threads the lead cites until the draft can be written from
receipts, not vibes. Same hands (read_file / grep / run_git / read_transcript),
same bounded budget, opposite verb. The shared pieces are imported from
agents.scout_agent rather than copied (separate by what changes — the prompt
and the output contract; share by what's stable — the hands and the spine
shape).

The Writer never flips lead status, never touches HTML, and never emits the
copyDraft stamp — provenance is stamped by the pipeline, mechanically, so it
cannot be forgotten or hallucinated.
"""
from __future__ import annotations

import json
from typing import Any

from anthropic import Anthropic

from agents.director_agent import _brief, _mark_cache_breakpoint
from agents.scout_agent import (
    _READ_TRANSCRIPT_DEF,
    _parse_json,
    _text_of,
    ScoutAgent,
    ScoutCall,
)
from pipelines.director.tools import TOOL_DEFS, ToolBox, default_toolbox

WRITER_MAX_TOKENS = 8192
# Same context-blowout guard as the Scout's roam; the convergent roam should
# come in well under it.
WRITER_MAX_TOOL_CHARS = 120_000

_ROAM_TOOL_NAMES = {"read_file", "grep", "run_git"}


WRITER_NOTE_PROMPT = """You are the Writer — the uzelhub newsroom's rewrite desk. An Editor has claimed a lead and assigned it to you. Your job is the middle of the pipeline: claimed lead in, draft out. Downstream, a deterministic generator renders your draft and the Editor approves it; you never publish, never route, never touch HTML.

REGISTER: field note — the apex /notes/ section, man-page dry. Field notes are the ecosystem's self-awareness first, war stories second: the platform describing its own workings honestly. Honesty about failure is the register's whole credibility — the moment it crows, it's dead.

SHAPE (Editor's standing order, 2026-07-16; amended 2026-07-17): three beats — the problem, the solution, the lessons learned. A field note fits on one screen; it is not the long-form telling. Keep the receipts, cut the play-by-play: every detail that survives must earn its line. Long-form depth belongs to the blog leg, which retells the story and links back to the note. Two scannability rules: (1) receipts that enumerate — commits, read histories, fix steps — go in a list body entry, never buried in a sentence; the list carries the full receipt (hash AND subject line, not "three commits"). (2) Recurring house terms may be cited in the "context" field (keys into uzelhub-web/marketing/data/lexicon.json — read it before choosing); the generator renders a Quick-context block from ONLY the cited keys. Cite only terms the body actually uses, 4 at most; a term missing from the lexicon is introduced inline instead (smart stranger) — never define lexicon terms yourself.

INVESTIGATE CONVERGENTLY. The lead cites its sources; pull exactly those threads before writing:
- read_transcript — ingested session-log rows by seq (when a lead cites sessions/turns, grep the repos for context first if you need to locate seqs).
- read_file / grep — the repos and docs on the box (design docs, the sysadmin ledger, devlogs, the marketing survey).
- run_git — read-only git (log / show / blame) when the story turns on when-and-why.
Write from what the box actually said. If a fact is not in your sources, pull the thread further or write around it — NEVER invent a detail, a date, or a number. Your tool budget is small: when you can write from receipts, stop investigating and write.

REDACTION (absolute): transcripts contain credentials, keys, internal paths, personal data. Never reproduce secret material — paraphrase and point. Your draft parks unpublished behind a scrub gate and the Editor's approval, but write as if that gate did not exist.

VOICE: you have no voice of your own. The exemplar below carries the voice — study how it moves, not just what it says. The named moves are handles, used sparingly.

Your FINAL message must be STRICT JSON, nothing else — a single note entry:
{"slug": "<kebab-case, may reuse the lead's>", "kicker": "Field note", "date": "<Month YYYY>",
 "title": "<the dry hook — a fact that lands>",
 "tagline": "<one sentence, receipt-forward>",
 "metaDescription": "<~155 chars, search-facing>",
 "bullets": ["<3-5 short receipt-forward lines>"],
 "image": {"label": "<optional diagram slot — describe it, or omit the key entirely>"},
 "context": ["<lexicon keys the note's body uses — omit the key entirely if none apply>"],
 "sections": [{"h": "<heading>", "body": ["<paragraph>", {"list": ["<item>", "..."]}, {"numbered": ["<step>", "..."]}, "..."]}, ...],
 "sources": ["<the pointers you actually drew on — session/turns, files, commits>"]}
Do NOT include a copyDraft field — provenance is stamped by the pipeline, not by you."""


def _assignment_text(lead: dict) -> str:
    src = "\n".join(f"  - {s}" for s in lead.get("sources", []) or ["(none given)"])
    return (
        "THE ASSIGNMENT — a claimed lead from the ledger:\n"
        f"id: {lead.get('id')}\n"
        f"filed: {lead.get('filed')}  register: {lead.get('register')}\n"
        f"pitch: {lead.get('pitch', '')}\n"
        f"why_now: {lead.get('why_now', '')}\n"
        f"sources:\n{src}\n\n"
        "Investigate what you need, then deliver the note entry."
    )


class WriterAgent:
    def __init__(
        self,
        client: Anthropic,
        model: str,
        fallback_model: str,
        bottle: str,
        roam_iterations: int = 6,
        toolbox: ToolBox | None = None,
    ) -> None:
        self.client = client
        self.model = model
        self.fallback_model = fallback_model
        self.roam_iterations = roam_iterations
        self.toolbox = toolbox if toolbox is not None else default_toolbox()
        self.roam_tools = [d for d in TOOL_DEFS if d["name"] in _ROAM_TOOL_NAMES] + [
            _READ_TRANSCRIPT_DEF
        ]
        # Prompt + bottle form one stable system block (one cache breakpoint);
        # only the assignment varies per run.
        self.system = WRITER_NOTE_PROMPT + "\n\n" + bottle

    def _plain(self, model: str, user: str) -> ScoutCall:
        resp = self.client.messages.create(
            model=model,
            max_tokens=WRITER_MAX_TOKENS,
            system=self.system,
            messages=[{"role": "user", "content": user}],
        )
        call = ScoutCall(data=_parse_json(_text_of(resp)), model=model, raw_text=_text_of(resp))
        ScoutAgent._tally(call, resp)
        call.stop_reason = resp.stop_reason
        return call

    def draft(self, lead: dict, conn=None) -> ScoutCall:
        """Bounded convergent roam + the draft. Mirrors the Scout's synthesize
        loop: on stop_reason=refusal, retry once tool-less on the fallback."""
        user = _assignment_text(lead)
        call = ScoutCall(data={}, model=self.model)
        messages: list[dict[str, Any]] = [{"role": "user", "content": user}]
        tool_chars = 0
        response = None

        def _create(tool_choice: Any | None = None):
            kwargs: dict[str, Any] = dict(
                model=self.model,
                max_tokens=WRITER_MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": self.system,
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
            _mark_cache_breakpoint(messages)
            response = _create()
            ScoutAgent._tally(call, response)
            if response.stop_reason == "refusal":
                fb = self._plain(self.fallback_model, user)
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
                        out, is_err = ScoutAgent._read_transcript(conn, args)
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
            if tool_chars >= WRITER_MAX_TOOL_CHARS:
                break  # roam budget spent — force the draft

        finished = response is not None and response.stop_reason != "tool_use"
        if not finished:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Roam budget reached. Stop investigating and deliver the "
                        "note entry now — strict JSON only."
                    ),
                }
            )
            _mark_cache_breakpoint(messages)
            response = _create(tool_choice={"type": "none"})
            ScoutAgent._tally(call, response)

        call.raw_text = _text_of(response)
        call.data = _parse_json(call.raw_text)
        call.stop_reason = response.stop_reason
        return call
