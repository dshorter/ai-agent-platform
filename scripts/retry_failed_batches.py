"""Re-process pipeline_inputs rows that don't have a corresponding posts row.

Use case: a batch wrote its pipeline_inputs row but a downstream LLM-output
parse error (or transient API failure) caused the per-batch try/except in
runner.py to skip the post creation. This script picks those orphan inputs,
reconstructs the CommitBatch from the stored event_payload, and runs each
through the same content → extract → package → ghost flow.

Run as:
    set -a && source .env && set +a
    .venv/bin/python -m scripts.retry_failed_batches

Idempotent: relies on Ghost's slug uniqueness and the posts.ghost_post_id
unique constraint (ON CONFLICT DO UPDATE). Safe to re-run.
"""
from __future__ import annotations

import logging
import sys
import uuid

import psycopg
from anthropic import Anthropic
from slugify import slugify

from agents.content_agent import CommitBatch as AgentCommitBatch, ContentAgent
from agents.marketer_agent import LinkCandidate, MarketerAgent
from pipelines.blog_pipeline.config import PipelineConfig
from pipelines.blog_pipeline.ghost_publisher import GhostClient, GhostDraft
from pipelines.blog_pipeline.logging_context import (
    DecisionWriter,
    SequenceAwareLogManager,
)
from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.blog_pipeline.runner import _body_to_html, _record_post


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    config = PipelineConfig.from_env()

    conn = psycopg.connect(config.postgres_dsn)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pi.input_id, pi.event_payload, pi.commit_range_start, pi.commit_range_end
            FROM pipeline_inputs pi
            LEFT JOIN posts p ON p.input_id = pi.input_id
            WHERE p.post_id IS NULL
            ORDER BY pi.input_id
            """
        )
        orphans = cur.fetchall()

    if not orphans:
        print("No orphan pipeline_inputs rows. Nothing to do.")
        return 0

    print(f"Found {len(orphans)} orphan inputs to retry.")

    client = Anthropic(api_key=config.anthropic_api_key)
    content = ContentAgent(client)
    marketer = MarketerAgent(client)
    ghost = GhostClient(config.ghost_admin_url, config.ghost_admin_api_key)

    log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
    run_id = str(uuid.uuid4())

    # Record this retry as its own pipeline_run for clean attribution.
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_runs (run_id, pipeline_name, target_site, status)
            VALUES (%s, 'blog_pipeline.retry', 'uzelhub.com', 'running')
            """,
            (run_id,),
        )
        conn.commit()

    succeeded = 0
    failed = 0
    run_cost_usd = 0.0
    logger = logging.getLogger("uzelhub_crew.retry")

    with log_manager.task_sequence(run_id, "blog_pipeline.retry") as _task:
        for input_id, event_payload, start_sha, end_sha in orphans:
            commits = event_payload.get("commits", [])
            print(f"\n→ retrying input_id={input_id} ({len(commits)} commits, {start_sha[:8]}..{end_sha[:8]})")

            try:
                with log_manager.tool_sequence(
                    "content_agent", f"retry draft from {start_sha[:8]}"
                ) as ctx:
                    agent_batch = AgentCommitBatch(
                        source_repo=config.source_repo_name,
                        commits=commits,
                        project_context=config.project_context,
                    )
                    draft = content.draft(agent_batch)
                    ctx.llm_model = content.model
                    ctx.llm_provider = "anthropic"
                    ctx.token_count_input = draft.input_tokens
                    ctx.token_count_output = draft.output_tokens
                    ctx.token_count_cache_create = draft.cache_creation_input_tokens
                    ctx.token_count_cache_read = draft.cache_read_input_tokens
                    ctx.cost_usd = compute_cost(
                        ctx.llm_model,
                        ctx.token_count_input,
                        ctx.token_count_output,
                        ctx.token_count_cache_create,
                        ctx.token_count_cache_read,
                    )
                run_cost_usd += ctx.cost_usd or 0.0

                with log_manager.tool_sequence(
                    "marketer_agent.extract", "retry descriptor extraction"
                ) as ctx:
                    descriptor, usage = marketer.extract_descriptor(draft)
                    ctx.llm_model = marketer.extraction_model
                    ctx.llm_provider = "anthropic"
                    ctx.token_count_input = usage["input_tokens"]
                    ctx.token_count_output = usage["output_tokens"]
                    ctx.token_count_cache_create = usage.get(
                        "cache_creation_input_tokens", 0
                    )
                    ctx.token_count_cache_read = usage.get(
                        "cache_read_input_tokens", 0
                    )
                    ctx.cost_usd = compute_cost(
                        ctx.llm_model,
                        ctx.token_count_input,
                        ctx.token_count_output,
                        ctx.token_count_cache_create,
                        ctx.token_count_cache_read,
                    )
                run_cost_usd += ctx.cost_usd or 0.0

                with log_manager.tool_sequence(
                    "marketer_agent.package", "retry SEO packaging"
                ) as ctx:
                    packaged = marketer.package(
                        draft, descriptor, [], queue_depth=0
                    )
                    ctx.llm_model = marketer.marketer_model
                    ctx.llm_provider = "anthropic"
                    ctx.token_count_input = packaged.input_tokens
                    ctx.token_count_output = packaged.output_tokens
                    ctx.token_count_cache_create = packaged.cache_creation_input_tokens
                    ctx.token_count_cache_read = packaged.cache_read_input_tokens
                    ctx.cost_usd = compute_cost(
                        ctx.llm_model,
                        ctx.token_count_input,
                        ctx.token_count_output,
                        ctx.token_count_cache_create,
                        ctx.token_count_cache_read,
                    )
                run_cost_usd += ctx.cost_usd or 0.0

                with log_manager.tool_sequence(
                    "ghost.create_draft", f"retry publish {packaged.slug}"
                ) as ctx:
                    body_html = _body_to_html(packaged.body)
                    result = ghost.create_draft(
                        GhostDraft(
                            title=packaged.title,
                            slug=packaged.slug or slugify(packaged.title),
                            html=body_html,
                            tags=packaged.tags,
                            meta_description=packaged.meta_description,
                        )
                    )
                    ctx.payload = {
                        "ghost_post_id": result.post_id,
                        "ghost_url": result.url,
                        "source_input_id": input_id,
                    }
                    _record_post(
                        conn,
                        run_id=run_id,
                        input_id=input_id,
                        target_site="uzelhub.com",
                        packaged=packaged,
                        body_html=body_html,
                        ghost_post_id=result.post_id,
                        ghost_url=result.url,
                    )

                succeeded += 1
                print(f"  ✓ recovered: {packaged.slug}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                logger.error(
                    "retry.batch_failed",
                    extra={
                        "input_id": input_id,
                        "start_sha": start_sha[:8],
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                print(f"  ✗ still failed: {type(exc).__name__}: {exc}")

    # Mark the retry run finished.
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE pipeline_runs SET status = 'success', completed_at = now()
            WHERE run_id = %s
            """,
            (run_id,),
        )
        conn.commit()

    ghost.close()
    print(f"\nRetry summary: {succeeded} recovered, {failed} still failed, ${run_cost_usd:.4f} spent.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
