"""
Commit-to-blog pipeline runner — the cron entry point.

Flow:
  1. Read new commits from the source repo via git_reader
  2. Filter trivial commits, group the rest into story batches
  3. For each batch: Content agent drafts, Marketer extracts descriptor
  4. After all drafts exist: Marketer packages with full-corpus link candidates
  5. Publish each package as a Ghost draft (idempotent by slug)

Everything runs inside a task_sequence so agent_decisions gets the full
decision trail. Blog Director reviews in Ghost admin; publish cadence is handled
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
from pipelines.blog_pipeline.logging_context import (
    DecisionWriter,
    SequenceAwareLogManager,
)
from pipelines.blog_pipeline.pricing import compute_cost


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


def _start_run(conn, run_id: str, pipeline_name: str, target_site: str) -> None:
    if conn is None:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_runs (run_id, pipeline_name, target_site, status)
            VALUES (%s, %s, %s, 'running')
            """,
            (run_id, pipeline_name, target_site),
        )
        conn.commit()


def _finish_run(conn, run_id: str, status: str, error: str | None = None) -> None:
    if conn is None:
        return
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE pipeline_runs
            SET completed_at = NOW(),
                status = %s,
                error_message = %s,
                duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
            WHERE run_id = %s
            """,
            (status, error, run_id),
        )
        conn.commit()


def _record_input(
    conn, run_id: str, source_repo: str, batch: CommitBatch
) -> int | None:
    if conn is None:
        return None
    from psycopg.types.json import Jsonb

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pipeline_inputs (
                run_id, source_type, source_repo,
                commit_range_start, commit_range_end,
                commit_count, event_payload
            )
            VALUES (%s, 'git_commits', %s, %s, %s, %s, %s)
            RETURNING input_id
            """,
            (
                run_id,
                source_repo,
                batch.start_sha,
                batch.end_sha,
                len(batch.commits),
                Jsonb({"commits": [c.to_dict() for c in batch.commits]}),
            ),
        )
        input_id = cur.fetchone()[0]
        conn.commit()
    return input_id


def _record_post(
    conn,
    *,
    run_id: str,
    input_id: int,
    target_site: str,
    packaged: "MarketerOutput",
    body_html: str,
    ghost_post_id: str,
    ghost_url: str,
) -> int | None:
    """Insert a row into posts so commit→article traceability is one FK hop.

    Idempotent on ghost_post_id — if Ghost returned an existing draft, we just
    refresh the row instead of inserting a duplicate."""
    if conn is None:
        return None
    from psycopg.types.json import Jsonb

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO posts (
                run_id, input_id, target_site, title, slug, body, body_html,
                meta_description, tags, series, primary_keyword, descriptor,
                ghost_post_id, ghost_url, status, suggested_publish_date
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, 'draft', %s
            )
            ON CONFLICT (ghost_post_id) DO UPDATE SET
                title = EXCLUDED.title,
                slug = EXCLUDED.slug,
                body = EXCLUDED.body,
                body_html = EXCLUDED.body_html,
                meta_description = EXCLUDED.meta_description,
                tags = EXCLUDED.tags,
                series = EXCLUDED.series,
                primary_keyword = EXCLUDED.primary_keyword,
                descriptor = EXCLUDED.descriptor,
                updated_at = now()
            RETURNING post_id
            """,
            (
                run_id, input_id, target_site,
                packaged.title, packaged.slug, packaged.body, body_html,
                packaged.meta_description, packaged.tags,
                packaged.series, packaged.descriptor.primary_keyword,
                Jsonb(packaged.descriptor.__dict__),
                ghost_post_id, ghost_url, packaged.suggested_publish_date,
            ),
        )
        post_id = cur.fetchone()[0]
        conn.commit()
    return post_id


def run(
    config: PipelineConfig,
    *,
    dry_run: bool = False,
    max_batches: int | None = None,
    pipeline_name: str = "blog_pipeline",
    target_site: str = "uzelhub.com",
) -> None:
    logger = logging.getLogger("uzelhub_crew.runner")

    conn = None
    if not dry_run:
        import psycopg

        conn = psycopg.connect(config.postgres_dsn)

    log_manager = SequenceAwareLogManager(
        db_writer=DecisionWriter(conn) if conn is not None else None
    )
    run_id = str(uuid.uuid4())
    _start_run(conn, run_id, pipeline_name, target_site)

    try:
        with log_manager.task_sequence(run_id, "blog_pipeline.run") as _task:
            reader = GitReader(config.source_repo_path)
            since = _since_sha(conn, config.source_repo_name)
            raw_commits = reader.log(since_sha=since)

            logger.info(
                "reader.loaded",
                extra={"commit_count": len(raw_commits), "since": since},
            )
            if not raw_commits:
                _finish_run(conn, run_id, "success")
                return

            commits = filter_trivial(raw_commits)
            batches = group_into_batches(commits)
            if max_batches is not None:
                batches = batches[:max_batches]
            logger.info(
                "batcher.grouped",
                extra={
                    "kept": len(commits),
                    "dropped": len(raw_commits) - len(commits),
                    "batch_count": len(batches),
                    "max_batches": max_batches,
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
            ghost = GhostClient(
                config.ghost_admin_url, config.ghost_admin_api_key
            )

            # Pass 1 — draft every batch and extract descriptors. No linking yet.
            drafts: list[tuple[Draft, Any, CommitBatch, int | None]] = []
            for batch in batches:
                input_id = _record_input(
                    conn, run_id, config.source_repo_name, batch
                )
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
                    ctx.cost_usd = compute_cost(
                        ctx.llm_model, ctx.token_count_input, ctx.token_count_output
                    )

                with log_manager.tool_sequence(
                    "marketer_agent.extract", "descriptor extraction"
                ) as ctx:
                    descriptor, usage = marketer.extract_descriptor(draft)
                    ctx.llm_model = marketer.extraction_model
                    ctx.llm_provider = "anthropic"
                    ctx.token_count_input = usage["input_tokens"]
                    ctx.token_count_output = usage["output_tokens"]
                    ctx.cost_usd = compute_cost(
                        ctx.llm_model, ctx.token_count_input, ctx.token_count_output
                    )

                drafts.append((draft, descriptor, batch, input_id))

            # Pass 2 — package each draft with link candidates drawn from the full corpus.
            for draft, descriptor, batch, input_id in drafts:
                candidates: list[LinkCandidate] = []
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
                    ctx.cost_usd = compute_cost(
                        ctx.llm_model, ctx.token_count_input, ctx.token_count_output
                    )

                # Pass 3 — POST to Ghost as a draft. Idempotent by slug.
                with log_manager.tool_sequence(
                    "ghost.create_draft", f"publish draft {packaged.slug}"
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
                        target_site=target_site,
                        packaged=packaged,
                        body_html=body_html,
                        ghost_post_id=result.post_id,
                        ghost_url=result.url,
                    )

            ghost.close()
        _finish_run(conn, run_id, "success")
    except Exception as exc:
        _finish_run(conn, run_id, "error", str(exc))
        raise
    finally:
        if conn is not None:
            conn.close()


def _body_to_html(markdown_body: str) -> str:
    """Render markdown to HTML for Ghost. Mermaid fences become <pre class="mermaid">
    blocks so the site-wide mermaid loader (Ghost code injection) renders them."""
    from markdown_it import MarkdownIt
    from markdown_it.common.utils import escapeHtml

    md = MarkdownIt("commonmark", {"html": False, "linkify": True})

    default_fence = md.renderer.rules.get("fence")

    def render_fence(tokens, idx, options, env):
        token = tokens[idx]
        info = (token.info or "").strip().lower()
        if info == "mermaid":
            return (
                "<!--kg-card-begin: html-->"
                f'<pre class="mermaid">{escapeHtml(token.content)}</pre>'
                "<!--kg-card-end: html-->\n"
            )
        return default_fence(tokens, idx, options, env)

    md.renderer.rules["fence"] = render_fence
    return md.render(markdown_body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Uzelhub commit-to-blog pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM and DB calls")
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Cap the number of batches processed (useful for first live run)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    config = PipelineConfig.from_env()
    run(config, dry_run=args.dry_run, max_batches=args.max_batches)
    return 0


if __name__ == "__main__":
    sys.exit(main())
