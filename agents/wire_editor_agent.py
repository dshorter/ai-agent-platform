"""The Wire Editor — the newsroom's triage desk, plus the Editor-in-chief's
shadow seat. Spec: docs/uzelhub-crew/publishing-automation-plan.md Phase 2.

Two plain calls, no tools:

  * triage  — the Wire Editor reads the full new-lead queue (the one context
    that legitimately holds the whole ledger haystack) and proposes a
    verdict per lead. This desk exists precisely so the Director never
    hauls this working set (the hire's context firewall).
  * shadow  — the Editor-in-chief (the Director's editorial hat, distinct
    from its morning-brief ops hat) reviews the compressed shortlist and
    stakes agree/differ per proposal. Shadow verdicts are the concordance
    metric that eventually hands the Director the routing pen (gate ①);
    until then nothing it says touches the ledger.

Neither call writes anything. Proposals land in a gitignored artifact; the
operator applies verdicts via lead_mark (the ledger's only pen). Proposals
flow toward the Editor only — never back to the Scout (pineapple rule).
"""
from __future__ import annotations

from anthropic import Anthropic

from agents.scout_agent import ScoutAgent, ScoutCall, _parse_json, _text_of

# Sized by day-one measurement, twice: a backlog queue needs ~80 visible
# tokens per proposal PLUS the model's (invisible) thinking, which measured
# ~4x the visible JSON on a 15-lead probe and scales with the queue — 32k
# still truncated on 113 leads. Set to the model's output ceiling; tokens
# are only billed as generated, and truncation guards refuse loudly anyway.
WIRE_MAX_TOKENS = 64000

WIRE_TRIAGE_PROMPT = """You are the Wire Editor — the uzelhub newsroom's triage desk. The Scout files story leads faster than the apex publishes (1-2 URLs/week); your job is turning the raw queue into a shortlist a human editor can dispose of in two minutes. You propose; you never decide — the operator applies verdicts, and nothing you write reaches the Scout.

Per NEW lead, propose exactly one verdict:
- claim — worth a Writer assignment; also confirm or correct the register.
- spike — not a story, a duplicate, or spent. Spikes are cheap and are NOT feedback to anyone; judge only this lead, never "this kind of lead."
- hold — real story, not ripe (an arc still accumulating, a dependency unshipped). Say what it waits for.

Registers (the routing table): note = durable field note, the platform's self-awareness first, war story second; blog = narrative retelling for developers; newsletter = weekly digest item; ticker = terse verb line for the pulse.

Judgment rules:
- Cluster leads that are the same story from different angles; propose claiming the strongest telling and spiking or holding the rest INTO it (say which).
- Check overlap against the already-claimed/drafted/published/spiked lists provided — the apex never tells the same story twice.
- Leads sourced from the day-job corpus (work-machine sessions) carry the employer gate: flag them "employer-gate" (publishable only technique-forward, application-anonymous). The flag informs the human gates downstream; it is not a spike reason.
- Be decisive. The drip is 1-2/week; a shortlist that claims everything triages nothing.

Output STRICT JSON, nothing else:
{"clusters": [{"theme": "<a few words>", "ids": ["<lead id>", ...]}],
 "proposals": [{"id": "<lead id>", "verdict": "claim|spike|hold",
                "register": "note|blog|newsletter|ticker",
                "reason": "<one tight line>",
                "flags": ["employer-gate"]}]}
Every new lead gets exactly one proposal. `flags` may be omitted when empty."""

CHIEF_SHADOW_PROMPT = """You are the Editor-in-chief of the uzelhub newsroom — the Director's editorial hat. The Wire Editor has triaged the new-lead queue into the shortlist below. Your job is the shadow routing: per proposal, stake your own position. You are being measured — your concordance with the human editor's eventual verdicts is the metric that decides when you inherit the routing pen. Judge honestly; do not rubber-stamp, do not contrarian-signal.

Per proposal: agree, or differ (with your verdict: claim|spike|hold and register). One tight reason either way — a reason that would survive being read next to the human's actual decision.

Editorial policy you route by: the apex publishes 1-2/week (capacity is the scarcest resource); field notes are self-awareness first, war stories second; a story has exactly one canonical home; employer-gate leads publish only technique-forward and application-anonymous; receipts must plausibly exist for a claim to be draftable. Routing only — the Scout's taste in surfacing is never your business.

Output STRICT JSON, nothing else:
{"shadow": [{"id": "<lead id>", "stance": "agree|differ",
             "verdict": "claim|spike|hold", "register": "note|blog|newsletter|ticker",
             "reason": "<one tight line>"}]}
Include verdict+register always (repeat the Wire Editor's when you agree)."""


class WireEditorAgent:
    def __init__(self, client: Anthropic, wire_model: str, chief_model: str) -> None:
        self.client = client
        self.wire_model = wire_model
        self.chief_model = chief_model

    def _plain(self, model: str, system: str, user: str) -> ScoutCall:
        # Streamed because 32k max_tokens exceeds the SDK's non-streaming
        # ceiling; the final message object is identical either way.
        with self.client.messages.stream(
            model=model,
            max_tokens=WIRE_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            resp = stream.get_final_message()
        call = ScoutCall(data=_parse_json(_text_of(resp)), model=model, raw_text=_text_of(resp))
        ScoutAgent._tally(call, resp)
        call.stop_reason = resp.stop_reason
        return call

    def triage(self, queue_text: str) -> ScoutCall:
        return self._plain(self.wire_model, WIRE_TRIAGE_PROMPT, queue_text)

    def shadow(self, shortlist_text: str) -> ScoutCall:
        return self._plain(self.chief_model, CHIEF_SHADOW_PROMPT, shortlist_text)
