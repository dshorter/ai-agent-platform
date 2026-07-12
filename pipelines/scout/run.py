"""One prospecting pass: walk N pages -> synthesize -> file leads.

Same stateless shape as the rest of the crew: connect, read fresh, reason,
persist to agent_decisions, exit. Every LLM call logs model/tokens/cost to the
spine, so the Sonnet-vs-Fable synthesis A/B (NEWSROOM §Model tiers) prices
itself automatically.

Dry-run is fully read-only: no cursor advance, no scratchpad writes, no map
appends, no leads filed — coverage is not consumed by a rehearsal.
"""
from __future__ import annotations

import logging
from datetime import date

import psycopg
from anthropic import Anthropic

from agents.scout_agent import ScoutAgent, ScoutCall
from pipelines.blog_pipeline.logging_context import (
    DecisionWriter,
    SequenceAwareLogManager,
)
from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.director.store import complete_run, create_run
from pipelines.scout import leads as leads_mod
from pipelines.scout import walk
from pipelines.scout.config import ScoutConfig
from pipelines.scout.sources import cross_agent_sequences

log = logging.getLogger("uzelhub_crew.scout")


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


def run_pass(config: ScoutConfig, dry_run: bool = False) -> dict:
    conn = psycopg.connect(config.postgres_dsn)
    log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
    agent = ScoutAgent(
        Anthropic(api_key=config.anthropic_api_key),
        walk_model=config.walk_model,
        synthesis_model=config.synthesis_model,
        synthesis_fallback=config.synthesis_fallback,
    )

    run_id = create_run(conn, "scout")
    status = "success"
    summary: dict = {"pages": 0, "rows": 0, "jewels": 0, "leads": [], "cost_usd": 0.0}
    try:
        with log_manager.task_sequence(
            task_id=str(run_id), description="scout: prospecting pass"
        ):
            cursor = walk.load_cursor(config.state_dir)
            jewels: list[dict] = []
            cost = 0.0

            # --- the walk: bounded pages, forward-only, logs-cursor only ---
            for page_no in range(config.walk_pages):
                rows = walk.fetch_page(conn, cursor, config.page_rows)
                if not rows:
                    break
                with log_manager.tool_sequence(
                    "scout_walk", reason=f"page {page_no + 1}, seq > {cursor}"
                ) as ctx:
                    call = agent.triage(walk.page_as_prompt(rows))
                    page_jewels = call.data.get("jewels", []) or []
                    pad_notes = call.data.get("scratchpad", []) or []
                    map_notes = call.data.get("map_notes", []) or []
                    cost += _record(
                        ctx,
                        call,
                        {
                            "rows": len(rows),
                            "seq_range": [rows[0]["seq"], rows[-1]["seq"]],
                            "jewels": len(page_jewels),
                            "scratchpad_notes": len(pad_notes),
                            "dry_run": dry_run,
                        },
                    )
                jewels.extend(page_jewels)
                summary["pages"] += 1
                summary["rows"] += len(rows)
                cursor = rows[-1]["seq"]
                if not dry_run:
                    walk.apply_scratchpad(conn, pad_notes, {r["seq"] for r in rows})
                    walk.append_map_notes(
                        config.state_dir, map_notes, date.today().isoformat()
                    )
                    walk.save_cursor(config.state_dir, cursor)
                if cost >= config.max_cost_usd:
                    log.warning("scout.pass cost cap hit during walk (%.4f)", cost)
                    break

            # --- the free-roam side + the leap ---
            sequences = cross_agent_sequences(conn)
            pitched = leads_mod.load_pitched(config.leads_path)
            with log_manager.tool_sequence(
                "scout_synthesis", reason=f"{len(jewels)} jewels, {len(sequences)} sequences"
            ) as ctx:
                call = agent.synthesize(
                    {
                        "jewels": jewels,
                        "sequences": sequences,
                        "map": walk.read_map(config.state_dir),
                        "pitched": pitched,
                    }
                )
                new_leads = call.data.get("leads", []) or []
                cost += _record(
                    ctx,
                    call,
                    {
                        "leads": len(new_leads),
                        "fallback_used": call.fallback_used,
                        "stop_reason": call.stop_reason,
                        "dry_run": dry_run,
                    },
                )

            summary["jewels"] = len(jewels)
            summary["leads"] = new_leads
            summary["cost_usd"] = round(cost, 4)
            summary["synthesis_model"] = call.model

            if not dry_run and new_leads:
                filed = leads_mod.append_leads(config.leads_path, new_leads, call.model)
                summary["filed"] = filed
        return summary
    except Exception:
        status = "error"
        raise
    finally:
        complete_run(conn, run_id, status)
        conn.close()
