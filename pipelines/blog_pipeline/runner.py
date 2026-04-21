"""
Commit-to-blog pipeline runner — the cron entry point.

Flow:
  1. Read new commits from the source repo via git_reader
  2. Filter trivial commits, group the rest into story batches
  3. For each batch: Content agent drafts, Marketer extracts descriptor
  4. After all drafts exist: Marketer packages with full-corpus link candidates
  5. Publish each package as a Ghost draft (idempotent by slug)

Everything runs inside a task_sequence so agent_decisions gets the full
decision trail. Director reviews in Ghost admin; publish cadence is handled
by a separate throttled job (not in Sprint Zero).
"""
from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import date
from typing import Any

from anthropic import Anthropic
from slugify import slugify

from agents.content_agent import CommitBatch as AgentCommitBatch, ContentAgent, Draft
from agents.marketer_agent import LinkCandidate, MarketerAgent, MarketerOutput
from pipelines.blog_pipeline.commit_batcher import (
    CommitBatch,
    filter_trivial,
    group_into_batches,
)
from pipelines.blog_pipeline.config import PipelineConfig
from pipelines.blog_pipeline.ghost_publisher import GhostClient, GhostDraft
from pipelines.blog_pipeline.git_reader import GitReader
from pipelines.blog_pipeline.logging_context import SequenceAwareLogManager


def _since_sha(conn, source_repo: str) -> str | None:
    """Read the most recent commit_range_end for this source repo."""
    if conn is None:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT commit_range_end
            FROM pipeline_inputs
            WHERE source_repo = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (source_repo,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def _record_input(conn, source_repo: str, batch: CommitBatch) -> int | None:
    if conn is None:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_inputs (
                source_repo, commit_range_start, commit_range_end,
                commit_count, event_payload
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING event_id
            """,
            (
                source_repo,
                batch.start_sha,
                batch.end_sha,
                len(batch.commits),
                {"commits": [c.to_dict() for c in batch.commits]},
            ),
        )
        event_id = cur.fetchone()[0]
        conn.commit()
    return event_id


def run(config: PipelineConfig, *, dry_run: bool = False) -> None:
    logger = logging.getLogger("uzelhub_crew.runner")

    conn = None
    if not dry_run:
        import psycopg

        conn = psycopg.connect(config.postgres_dsn)

    log_manager = SequenceAwareLogManager()
    task_id = str(uuid.uuid4())

    with log_manager.task_sequence(task_id, "blog_pipeline.run") as _task:
        reader = GitReader(config.source_repo_path)
        since = _since_sha(conn, config.source_repo_name)
        raw_commits = reader.log(since_sha=since)

        logger.info(
            "reader.loaded", extra={"commit_count": len(raw_commits), "since": since}
        )
        if not raw_commits:
            return

        commits = filter_trivial(raw_commits)
        batches = group_into_batches(commits)
        logger.info(
            "batcher.grouped",
            extra={
                "kept": len(commits),
                "dropped": len(raw_commits) - len(commits),
                "batch_count": len(batches),
            },
        )

        if dry_run:
            for b in batches:
                print(
                    f"[dry-run] batch {b.start_sha[:8]}..{b.end_sha[:8]} "
                    f"({len(b.commits)} commits, {b.total_lines} lines)"
                )
            return

        client = Anthropic(api_key=config.anthropic_api_key)
        content = ContentAgent(client)
        marketer = MarketerAgent(client)
        ghost = GhostClient(config.ghost_admin_url, config.ghost_admin_api_key)

        # Pass 1 — draft every batch and extract descriptors. No linking yet.
        drafts: list[tuple[Draft, Any, CommitBatch, int | None]] = []
        for batch in batches:
            event_id = _record_input(conn, config.source_repo_name, batch)
            with log_manager.tool_sequence(
                "content_agent", f"draft from {batch.start_sha[:8]}"
            ) as ctx:
                agent_batch = AgentCommitBatch(
                    source_repo=config.source_repo_name,
                    commits=[c.to_dict() for c in batch.commits],
                    project_context=config.project_context,
                )
                draft = content.draft(agent_batch)
                ctx.llm_model = content.model
                ctx.llm_provider = "anthropic"
                ctx.token_count_input = draft.input_tokens
                ctx.token_count_output = draft.output_tokens

            with log_manager.tool_sequence(
                "marketer_agent.extract", "descriptor extraction"
            ) as ctx:
                descriptor, usage = marketer.extract_descriptor(draft)
                ctx.llm_model = marketer.extraction_model
                ctx.llm_provider = "anthropic"
                ctx.token_count_input = usage["input_tokens"]
                ctx.token_count_output = usage["output_tokens"]

            drafts.append((draft, descriptor, batch, event_id))

        # Pass 2 — package each draft with link candidates drawn from the full corpus.
        for draft, descriptor, batch, event_id in drafts:
            candidates: list[LinkCandidate] = []  # filled by graph.rank_link_candidates after PR 2 migration lands
            with log_manager.tool_sequence(
                "marketer_agent.package", "SEO packaging"
            ) as ctx:
                packaged = marketer.package(
                    draft, descriptor, candidates, queue_depth=len(drafts)
                )
                ctx.llm_model = marketer.marketer_model
                ctx.llm_provider = "anthropic"
                ctx.token_count_input = packaged.input_tokens
                ctx.token_count_output = packaged.output_tokens

            # Pass 3 — POST to Ghost as a draft. Idempotent by slug.
            with log_manager.tool_sequence(
                "ghost.create_draft", f"publish draft {packaged.slug}"
            ) as ctx:
                result = ghost.create_draft(
                    GhostDraft(
                        title=packaged.title,
                        slug=packaged.slug or slugify(packaged.title),
                        html=_body_to_html(packaged.body),
                        tags=packaged.tags,
                        meta_description=packaged.meta_description,
                    )
                )
                ctx.payload = {
                    "ghost_post_id": result.post_id,
                    "ghost_url": result.url,
                    "source_event_id": event_id,
                }

        ghost.close()
        if conn is not None:
            conn.close()


def _body_to_html(markdown_body: str) -> str:
    """Placeholder. Ghost accepts HTML; we'll wire a real markdown renderer
    (markdown-it-py or similar) before hitting production."""
    paragraphs = [p.strip() for p in markdown_body.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{p}</p>" for p in paragraphs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Uzelhub commit-to-blog pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM and DB calls")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    config = PipelineConfig.from_env()
    run(config, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
