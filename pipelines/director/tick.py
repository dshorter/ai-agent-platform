"""Ambient ticks — the Director's scheduled, proactive runs.

Unlike the listener (reactive: waits for Dan to message), a tick is fired by a
timer. It runs one Director reasoning turn against a fixed prompt, then *pushes*
the reply to Dan's Telegram chat. Same stateless shape as the rest of the crew:
load state, read fresh, reason, persist to agent_decisions, exit.

    python -m pipelines.director --tick morning            # run + push to Telegram
    python -m pipelines.director --tick morning --dry-run  # run + print, no send

The reply *style* is governed by the persona (agents/director_agent.py); a tick
prompt only sets the *job* for this run. Delivery reuses the same outbound-only
Telegram client the listener uses — in a 1:1 chat the chat_id is Dan's user id.
"""
from __future__ import annotations

import logging
from datetime import date

import psycopg
from anthropic import Anthropic

from agents.director_agent import DIRECTOR_TICK_MAX_ITERATIONS, DirectorAgent
from pipelines.blog_pipeline.logging_context import (
    DecisionWriter,
    SequenceAwareLogManager,
)
from pipelines.director.config import DirectorConfig
from pipelines.director.listener import run_turn
from pipelines.director.telegram import TelegramClient


log = logging.getLogger("uzelhub_crew.director.tick")


MORNING_BRIEF = (
    "Morning brief. Read the projects fresh and give Dan a tight cross-project "
    "priority read for today: lead with the single most important next move, then "
    "the top 2-3 items in priority order with a one-line why each, and call out "
    "anything newly unblocked or newly stalled. This lands on his phone first "
    "thing, so keep it short and scannable and don't ask questions. If something "
    "is genuinely blocking, name it and what would clear it."
)

# name -> (header shown on Telegram, prompt fed to the Director)
TICKS: dict[str, tuple[str, str]] = {
    "morning": ("☀️ Morning brief", MORNING_BRIEF),
}


def run_tick(config: DirectorConfig, name: str, *, dry_run: bool = False) -> None:
    try:
        header, prompt = TICKS[name]
    except KeyError:
        raise SystemExit(
            f"unknown tick {name!r} — known: {', '.join(sorted(TICKS))}"
        )

    conn = psycopg.connect(config.postgres_dsn)
    try:
        log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
        director = DirectorAgent(
            Anthropic(api_key=config.anthropic_api_key),
            model=config.model,
            max_cost_usd=config.max_cost_usd,
            # Unattended: no one is waiting on the reply, so this path gets the
            # larger step budget (see DIRECTOR_TICK_MAX_ITERATIONS).
            max_iterations=DIRECTOR_TICK_MAX_ITERATIONS,
        )
        log.info("director.tick.start name=%s model=%s", name, config.model)
        # Reuse the spine: run_turn gathers fresh state, runs the agentic loop, and
        # persists the whole turn (reply + trace + cost) to agent_decisions.
        reply = run_turn(prompt, director, log_manager, conn, channel=f"tick:{name}")
    finally:
        conn.close()

    body = f"{header} — {date.today():%a %b %-d}\n\n{reply.text}"

    if dry_run:
        print(body)
        print(
            f"\n[dry-run: not sent — {reply.input_tokens} in / "
            f"{reply.output_tokens} out, iterations={reply.iterations}]"
        )
        return

    if not config.telegram_token or config.allowed_user_id is None:
        raise SystemExit(
            "cannot push tick — DIRECTOR_TELEGRAM_TOKEN / "
            "DIRECTOR_TELEGRAM_ALLOWED_USER not set. Use --dry-run to test without Telegram."
        )
    TelegramClient(config.telegram_token).send_message(config.allowed_user_id, body)
    log.info("director.tick.sent name=%s", name)
