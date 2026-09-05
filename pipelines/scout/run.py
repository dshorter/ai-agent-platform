"""The Scout's stages, and the three ways to run them.

Same stateless shape as the rest of the crew: connect, read fresh, reason,
persist to agent_decisions, exit. Every LLM call logs model/tokens/cost to the
spine, so the Sonnet-vs-Fable synthesis A/B (NEWSROOM §Model tiers) prices
itself automatically.

**The walk and the synthesis are separable** (scout-retool.md §2). They used to
be one indivisible act, which meant mining could not happen without also
storytelling — and since the walk is the cheap tier (~$0.0105 a page) while
synthesis is the premium one, re-mining the corpus cost ~$200 instead of ~$1.
Now:

    run_pass       walk, then synthesize over what that walk found — unchanged
                   in meaning, and still what the daily timer invokes.
    run_walk       mine an explicit range and persist the jewels. No synthesis,
                   no leads, no cursor movement. This is what makes a reclaim
                   sweep affordable.
    run_synthesis  read a jewel selection back out and surface leads from it.
                   The verb both future consumers of the jewel table grow from.

`run_pass` deliberately hands synthesis the jewels it holds **in memory** rather
than re-reading them from the table. The two are equivalent when the write
succeeded, and going through the database would make a storage hiccup silently
cost a pass its leads. Composition is at the function boundary, not the storage
one.

Dry-run is fully read-only: no cursor advance, no jewels, no scratchpad writes,
no map appends, no leads filed — coverage is not consumed by a rehearsal.
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
from pipelines.scout import jewels as jewels_mod
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


def _agent(config: ScoutConfig) -> ScoutAgent:
    return ScoutAgent(
        Anthropic(api_key=config.anthropic_api_key),
        walk_model=config.walk_model,
        synthesis_model=config.synthesis_model,
        synthesis_fallback=config.synthesis_fallback,
        roam_iterations=config.roam_iterations,
    )


# --- stage 1: the walk ---------------------------------------------------------


def _walk_stage(
    conn,
    agent: ScoutAgent,
    config: ScoutConfig,
    log_manager,
    run_id,
    cursor: int,
    row_budget: int | None,
    summary: dict,
    dry_run: bool,
    cursor_key: str | None,
    cost_cap: float | None,
    stop_at: int | None = None,
) -> tuple[list[dict], float, int]:
    """Mine pages forward from `cursor`. Returns (jewels, cost, new cursor).

    `cursor_key` is what separates the three callers: "forward" for a pass
    reading new ore, "backfill" for the same pass topping up from history, and
    None for a reclaim sweep, which re-reads ore the forward position already
    covered and must leave every position exactly where it was.

    `stop_at` bounds the backfill so it halts on catching up with forward
    rather than looping the corpus forever — a second sweep is an explicit
    operator act (reset the position to 0), not something that happens quietly.
    """
    found: list[dict] = []
    cost = 0.0
    page_no = 0
    remaining = row_budget
    while remaining is None or remaining > 0:
        # Trim the last page to the budget rather than overshooting it. The
        # budget protects synthesis conversion, and a plate 149 rows over is
        # still a bigger plate.
        take = config.page_rows if remaining is None else min(config.page_rows, remaining)
        rows = walk.fetch_page(conn, cursor, take)
        if stop_at is not None:
            rows = [r for r in rows if r["seq"] <= stop_at]
        if not rows:
            break
        page_no += 1
        with log_manager.tool_sequence(
            "scout_walk", reason=f"page {page_no}, seq > {cursor}"
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
        found.extend(page_jewels)
        summary["pages"] += 1
        summary["rows"] += len(rows)
        if remaining is not None:
            remaining -= len(rows)
        cursor = rows[-1]["seq"]
        if not dry_run:
            # Persist the mining before anything downstream consumes it, so a
            # crash between here and the leap costs nothing already paid for.
            summary["jewels_persisted"] += jewels_mod.persist(
                conn, page_jewels, rows, run_id, config.walk_model
            )
            walk.apply_scratchpad(conn, pad_notes, {r["seq"] for r in rows})
            walk.append_map_notes(config.state_dir, map_notes, date.today().isoformat())
            if cursor_key:
                walk.save_cursors(config.state_dir, **{cursor_key: cursor})
        if cost_cap is not None and cost >= cost_cap:
            log.warning("scout.walk cost cap hit (%.4f)", cost)
            break
    return found, cost, cursor


# --- stage 2: the leap ---------------------------------------------------------


def _synthesis_stage(
    conn,
    agent: ScoutAgent,
    config: ScoutConfig,
    log_manager,
    found: list[dict],
    summary: dict,
    dry_run: bool,
) -> float:
    sequences = cross_agent_sequences(conn)
    pitched = leads_mod.load_pitched(config.leads_path, config.pitch_digest_chars)
    with log_manager.tool_sequence(
        "scout_synthesis", reason=f"{len(found)} jewels, {len(sequences)} sequences"
    ) as ctx:
        call = agent.synthesize(
            {
                "jewels": found,
                "sequences": sequences,
                "map": walk.read_map(config.state_dir),
                "pitched": pitched,
            },
            conn=conn,
        )
        new_leads = call.data.get("leads", []) or []
        cost = _record(
            ctx,
            call,
            {
                "leads": len(new_leads),
                "fallback_used": call.fallback_used,
                "stop_reason": call.stop_reason,
                "iterations": call.iterations,
                "tool_calls": call.tool_calls,  # the foraging trace — the A/B's second axis
                "dry_run": dry_run,
            },
        )

    summary["jewels"] = len(found)
    summary["leads"] = new_leads
    summary["synthesis_model"] = call.model
    summary["roam"] = call.tool_calls

    if not dry_run and new_leads:
        summary["filed"] = leads_mod.append_leads(config.leads_path, new_leads, call.model)
    return cost


def _blank_summary() -> dict:
    return {
        "pages": 0,
        "rows": 0,
        "jewels": 0,
        "jewels_persisted": 0,
        "leads": [],
        "cost_usd": 0.0,
    }


# --- the three verbs -----------------------------------------------------------


def run_pass(config: ScoutConfig, dry_run: bool = False) -> dict:
    """Walk, then synthesize over what this walk found. The timer's entry point."""
    conn = psycopg.connect(config.postgres_dsn)
    log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
    agent = _agent(config)
    run_id = create_run(conn, "scout")
    status = "success"
    summary = _blank_summary()
    try:
        with log_manager.task_sequence(
            task_id=str(run_id), description="scout: prospecting pass"
        ):
            cursors = walk.load_cursors(config.state_dir)
            found, cost, _ = _walk_stage(
                conn, agent, config, log_manager, run_id,
                cursor=cursors["forward"],
                row_budget=config.pass_row_budget,
                summary=summary,
                dry_run=dry_run,
                cursor_key="forward",
                cost_cap=config.max_cost_usd,
            )
            # Fresh ore has first claim on the plate; backfill only gets what
            # is left. On a busy day it gets nothing, on a quiet one it gets
            # most of the budget — self-balancing, and no scheduling logic.
            # It stops at the forward position it started behind: catching up
            # means the corpus has been re-mined once, and a second sweep is
            # the operator's call.
            spare = config.pass_row_budget - summary["rows"]
            if spare > 0 and cursors["backfill"] < cursors["forward"]:
                back, back_cost, _ = _walk_stage(
                    conn, agent, config, log_manager, run_id,
                    cursor=cursors["backfill"],
                    row_budget=spare,
                    summary=summary,
                    dry_run=dry_run,
                    cursor_key="backfill",
                    cost_cap=config.max_cost_usd - cost,
                    stop_at=cursors["forward"],
                )
                found.extend(back)
                cost += back_cost
                summary["backfill_rows"] = summary["rows"] - (config.pass_row_budget - spare)
            cost += _synthesis_stage(
                conn, agent, config, log_manager, found, summary, dry_run
            )
            summary["cost_usd"] = round(cost, 4)
        return summary
    except Exception:
        status = "error"
        raise
    finally:
        complete_run(conn, run_id, status)
        conn.close()


def run_walk(
    config: ScoutConfig,
    from_seq: int = 0,
    max_pages: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Mine an explicit range and persist the jewels. No synthesis, no leads.

    Neither cursor moves: a reclaim sweep re-reads ore the forward position has
    already covered, and letting it write that position would rewind the Scout.
    Bounded by `max_pages` alone — the pass row budget exists to protect
    synthesis conversion, and there is no synthesis here to protect.
    """
    conn = psycopg.connect(config.postgres_dsn)
    log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
    agent = _agent(config)
    run_id = create_run(conn, "scout")
    status = "success"
    summary = _blank_summary()
    summary["run_id"] = str(run_id)
    summary["from_seq"] = from_seq
    try:
        with log_manager.task_sequence(
            task_id=str(run_id), description="scout: walk (mine only)"
        ):
            found, cost, last = _walk_stage(
                conn, agent, config, log_manager, run_id,
                cursor=from_seq,
                # Unbounded by default: the pass budget exists to protect
                # synthesis conversion, and there is no synthesis here.
                row_budget=(max_pages * config.page_rows) if max_pages else None,
                summary=summary,
                dry_run=dry_run,
                cursor_key=None,
                cost_cap=None,
            )
            summary["jewels"] = len(found)
            summary["last_seq"] = last
            summary["cost_usd"] = round(cost, 4)
        return summary
    except Exception:
        status = "error"
        raise
    finally:
        complete_run(conn, run_id, status)
        conn.close()


def run_synthesis(
    config: ScoutConfig,
    since: str | None = None,
    until: str | None = None,
    kinds: list[str] | None = None,
    of_run=None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    """Surface leads from jewels already on disk — no transcript is re-read."""
    conn = psycopg.connect(config.postgres_dsn)
    log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
    agent = _agent(config)
    run_id = create_run(conn, "scout")
    status = "success"
    summary = _blank_summary()
    try:
        with log_manager.task_sequence(
            task_id=str(run_id), description="scout: synthesis over stored jewels"
        ):
            found = jewels_mod.select(
                conn, since=since, until=until, kinds=kinds, run_id=of_run, limit=limit
            )
            summary["selected"] = len(found)
            if not found:
                log.warning("scout.synthesis selection is empty — nothing to leap from")
                return summary
            summary["cost_usd"] = round(
                _synthesis_stage(
                    conn, agent, config, log_manager, found, summary, dry_run
                ),
                4,
            )
        return summary
    except Exception:
        status = "error"
        raise
    finally:
        complete_run(conn, run_id, status)
        conn.close()
