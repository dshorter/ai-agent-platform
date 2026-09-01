"""One assignment: claimed lead -> convergent roam -> stamped draft.

Same stateless shape as the rest of the crew: connect, read fresh, reason,
persist to agent_decisions, exit. The draft parks in the gitignored state dir
with a code-generated copyDraft stamp — provenance is mechanical so it cannot
be forgotten or hallucinated. Nothing here writes the leads ledger (the
Editor's pen) or uzelhub-web (the scrub + approval gate's other side).

Dry-run rehearses on a lead of any status and persists nothing; a real run
requires status: claimed — the Writer takes assignments, it doesn't pull
stories off the pile."""
from __future__ import annotations

import json
import logging
from datetime import date

import psycopg
from anthropic import Anthropic

from agents.scout_agent import ScoutCall
from agents.writer_agent import WriterAgent
from pipelines.blog_pipeline.logging_context import (
    DecisionWriter,
    SequenceAwareLogManager,
)
from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.director.store import complete_run, create_run
from pipelines.writer import assignment
from pipelines.writer.bottle import load_profile
from pipelines.writer.config import REGISTER_PROFILES, WriterConfig

log = logging.getLogger("uzelhub_crew.writer")


def _record(ctx, call: ScoutCall, payload: dict) -> float:
    ctx.llm_model = call.model
    ctx.llm_provider = "anthropic"
    ctx.token_count_input = call.input_tokens
    ctx.token_count_output = call.output_tokens
    ctx.token_count_cache_create = call.cache_creation_input_tokens
    ctx.token_count_cache_read = call.cache_read_input_tokens
    cost = (
        compute_cost(
            call.model,
            call.input_tokens,
            call.output_tokens,
            call.cache_creation_input_tokens,
            call.cache_read_input_tokens,
        )
        or 0.0
    )
    ctx.cost_usd = cost
    ctx.payload = payload
    return cost


def _stamp(lead: dict, model: str) -> str:
    return (
        f"Draft {date.today().isoformat()} by the Writer ({model}) from lead "
        f"{lead['id']}. UNSCRUBBED: session-log-derived — hard secret/PII scrub "
        "AND Editor approval required before this entry crosses into "
        "uzelhub-web (public repo; a push is a publish)."
    )


def run_draft(config: WriterConfig, lead_id: str, dry_run: bool = False) -> dict:
    lead = assignment.find_lead(config.leads_path, lead_id)
    if lead is None:
        raise SystemExit(f"no lead '{lead_id}' on the ledger ({config.leads_path})")
    register = lead.get("register", "note")
    profile = REGISTER_PROFILES.get(register)
    if profile is None:
        raise SystemExit(
            f"lead '{lead_id}' is register '{register}' — the v1 desk handles "
            f"{sorted(REGISTER_PROFILES)} only (writer-persona.md §build order)"
        )
    if not dry_run and lead.get("status") not in ("claimed", "drafted"):
        raise SystemExit(
            f"lead '{lead_id}' is status '{lead.get('status')}' — the Editor "
            "claims (status: claimed) before the Writer drafts; drafted leads "
            "may be redrafted until approval; --dry-run to rehearse"
        )

    bottle = load_profile(config.voice_dir, profile)
    conn = psycopg.connect(config.postgres_dsn)
    log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
    agent = WriterAgent(
        Anthropic(api_key=config.anthropic_api_key),
        model=config.model,
        fallback_model=config.fallback_model,
        bottle=bottle,
        roam_iterations=config.roam_iterations,
    )

    run_id = create_run(conn, "writer")
    status = "success"
    summary: dict = {"lead": lead_id, "register": register, "profile": profile}
    try:
        with log_manager.task_sequence(
            task_id=str(run_id), description=f"writer: draft {lead_id}"
        ):
            with log_manager.tool_sequence("writer_draft", reason=lead_id) as ctx:
                call = agent.draft(lead, conn=conn)
                note = call.data if isinstance(call.data, dict) else {}
                cost = _record(
                    ctx,
                    call,
                    {
                        "lead": lead_id,
                        "register": register,
                        "delivered": bool(note.get("sections")),
                        "fallback_used": call.fallback_used,
                        "stop_reason": call.stop_reason,
                        "iterations": call.iterations,
                        "tool_calls": call.tool_calls,
                        "dry_run": dry_run,
                    },
                )
        summary.update(
            model=call.model,
            cost_usd=round(cost, 4),
            roam=call.tool_calls,
            delivered=bool(note.get("sections")),
        )
        if not note.get("sections"):
            summary["error"] = "no parsable note entry in the final message"
            summary["raw_tail"] = call.raw_text[-400:]
            return summary

        sources_cited = note.pop("sources", None) or lead.get("sources", [])
        note["copyDraft"] = _stamp(lead, call.model)
        if dry_run:
            summary["note"] = note
            return summary

        config.drafts_dir.mkdir(parents=True, exist_ok=True)
        draft_path = config.drafts_dir / f"{lead_id}.json"
        draft_path.write_text(
            json.dumps(
                {
                    "lead": lead,           # the assignment, for the Editor's desk
                    "sources_cited": sources_cited,  # stays behind at approval time
                    "roam": call.tool_calls,
                    # The desk's reasoning, when the seat asked for it. Sits
                    # beside the roam trace: roam says where it looked,
                    # reasoning says what it concluded. Never crosses over.
                    **({"reasoning": call.reasoning} if call.reasoning else {}),
                    "note": note,           # what crosses over after scrub + approval
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        summary["draft"] = str(draft_path)
        # Ledger lifecycle: a banked draft flips the lead claimed -> drafted
        # (lead_mark, the ledger's one mutation verb). Best-effort: the draft
        # write above already succeeded — a mark failure is a warning to the
        # operator, never a failed run. (Idempotent re-drafts of an already-
        # drafted lead refuse the mark; that's expected, not an error.)
        try:
            from pipelines.scout.lead_mark import mark

            summary["lead_marked"] = mark(lead_id, to="drafted", by="writer")
        except SystemExit as e:
            summary["lead_marked"] = f"not marked: {e}"
        return summary
    except Exception:
        status = "error"
        raise
    finally:
        complete_run(conn, run_id, status)
        conn.close()
