"""
Scout Agent — the newsroom's prospector, as two stages with opposite needs.

NEWSROOM §Model tiers: the Scout is not one model call. The WALK (triage over
big swaths of transcript — high token volume, low IQ demand) runs on the cheap
tier, inheriting the marketer's Haiku-extraction split. The SYNTHESIS (the
"link 16 things because maybe" leap — low volume, maximum IQ) runs on the
premium tier, env-var'd, Fable 5 by plan. Nothing filters the Scout's missing
leads, so the synthesis model sets the ceiling on what stories ever exist.

Both prompts hold the pineapple rule: aperture never narrows. Triage includes
when unsure; synthesis errs reckless; neither ever sees an Editor verdict.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from anthropic import Anthropic


SCOUT_TRIAGE_MAX_TOKENS = 4096
SCOUT_SYNTHESIS_MAX_TOKENS = 8192


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


SCOUT_SYNTHESIS_PROMPT = """You are the Scout's synthesis leap — the premium stage of the uzelhub newsroom's prospector. Over triaged transcript jewels, cross-agent decision sequences, and your own navigation map, surface STORY LEADS: the platform narrating its own building, curated into pitches an editor can route.

Generate WIDE. Bold many-way connections are welcome — the best stories are the ones no pattern predicted. False positives are cheap (an editor spikes them); missed leads are invisible and unrecoverable. Err reckless.

Weighting: a lead whose evidence spans multiple agents deserves extra weight (stories live at the seams between agents) — but span never disqualifies a lone-actor story; keep surfacing those too.

Dedup: skip only a lead whose pitch is essentially identical to one in the already-pitched list. Never generalize that list into "avoid this kind of story."

REDACTION (absolute): these transcripts contain credentials, keys, internal paths, personal data. Never reproduce secret material in a pitch — point to it (session id, turns, sequence id) and paraphrase the story around it.

Registers: ticker (terse verb line), newsletter (weekly digest item), note (durable field note — self-awareness first, war story second), blog (narrative retelling).

Output STRICT JSON, nothing else:
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
    raw_text: str = field(default="", repr=False)


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


class ScoutAgent:
    def __init__(
        self,
        client: Anthropic,
        walk_model: str,
        synthesis_model: str,
        synthesis_fallback: str,
    ) -> None:
        self.client = client
        self.walk_model = walk_model
        self.synthesis_model = synthesis_model
        self.synthesis_fallback = synthesis_fallback

    def _call(self, model: str, system: str, user: str, max_tokens: int) -> ScoutCall:
        resp = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            b.text for b in (resp.content or []) if getattr(b, "type", None) == "text"
        )
        u = resp.usage
        return ScoutCall(
            data=_parse_json(text),
            model=model,
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            cache_creation_input_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            stop_reason=resp.stop_reason,
            raw_text=text,
        )

    def triage(self, page_text: str) -> ScoutCall:
        return self._call(
            self.walk_model,
            SCOUT_TRIAGE_PROMPT,
            f"Transcript page:\n\n{page_text}",
            SCOUT_TRIAGE_MAX_TOKENS,
        )

    def synthesize(self, context: dict[str, Any]) -> ScoutCall:
        """One leap over the pass's triaged material. Handles the Fable caveat:
        on stop_reason=refusal, retry once on the fallback model (NEWSROOM
        §Model tiers — story-prospecting shouldn't trip the classifier, but
        wire the handling anyway)."""
        user = (
            "Jewels from this pass's transcript walk:\n"
            f"{json.dumps(context.get('jewels', []), indent=1)}\n\n"
            "Cross-agent decision sequences (agent_span = distinct agents touched; "
            "a weight, never a filter):\n"
            f"{json.dumps(context.get('sequences', []), indent=1)}\n\n"
            "Your navigation map (most recent notes):\n"
            f"{context.get('map', '(empty — first pass)')}\n\n"
            "Already-pitched (dedup ONLY — skip near-identical pitches, infer nothing else):\n"
            f"{json.dumps(context.get('pitched', []), indent=1)}\n\n"
            "Surface your leads."
        )
        call = self._call(
            self.synthesis_model, SCOUT_SYNTHESIS_PROMPT, user, SCOUT_SYNTHESIS_MAX_TOKENS
        )
        if call.stop_reason == "refusal":
            call = self._call(
                self.synthesis_fallback, SCOUT_SYNTHESIS_PROMPT, user, SCOUT_SYNTHESIS_MAX_TOKENS
            )
            call.fallback_used = True
        return call
