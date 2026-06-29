"""Walking-skeleton self-test — no Telegram required.

Runs one message through the Director agent and logs it to agent_decisions,
proving the reasoning + logging half of the loop with the live ANTHROPIC_API_KEY
and Postgres. The Telegram I/O half plugs in once the bot token exists.
"""
from __future__ import annotations

import psycopg
from anthropic import Anthropic

from agents.director_agent import DirectorAgent
from pipelines.blog_pipeline.logging_context import (
    DecisionWriter,
    SequenceAwareLogManager,
)
from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.director.config import DirectorConfig
from pipelines.director.listener import run_turn


def run_selftest(config: DirectorConfig, message: str) -> None:
    conn = psycopg.connect(config.postgres_dsn)
    log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
    director = DirectorAgent(
        Anthropic(api_key=config.anthropic_api_key),
        model=config.model,
        max_cost_usd=config.max_cost_usd,
    )

    print(f"\n>>> {message}\n")
    reply = run_turn(message, director, log_manager, conn, channel="selftest")
    print(f"<<< {reply.text}\n")

    cost = compute_cost(
        reply.model,
        reply.input_tokens,
        reply.output_tokens,
        reply.cache_creation_input_tokens,
        reply.cache_read_input_tokens,
    )
    print(
        f"[logged to agent_decisions — {reply.input_tokens} in / "
        f"{reply.output_tokens} out, ${cost or 0:.4f}, model {reply.model}]"
    )
    conn.close()
