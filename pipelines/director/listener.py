"""
Director listener — the Telegram switchboard + per-message run loop.

Walking skeleton: long-poll Telegram, whitelist Dan, route by slash command
(default -> director), run one reasoning turn, reply, and log the decision to
agent_decisions via the sequence-aware spine.
"""
from __future__ import annotations

import logging
import sys
import time

import psycopg
from anthropic import Anthropic

from agents.director_agent import DirectorAgent, DirectorReply
from pipelines.blog_pipeline.logging_context import (
    DecisionWriter,
    SequenceAwareLogManager,
)
from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.director.config import DirectorConfig
from pipelines.director.store import complete_run, create_run
from pipelines.director.telegram import TelegramClient, Update


log = logging.getLogger("uzelhub_crew.director")

# Agents reachable on the shared bot. Only `director` is wired in the walking
# skeleton; the rest are switchboard stubs.
KNOWN_AGENTS = {"director", "sysadmin", "blog"}


def route(text: str) -> tuple[str, str]:
    """(agent, message). A leading /agent slash-command routes; bare text -> director."""
    stripped = text.strip()
    if stripped.startswith("/"):
        head, _, rest = stripped[1:].partition(" ")
        if head.lower() in KNOWN_AGENTS:
            return head.lower(), rest.strip()
    return "director", stripped


def run_turn(
    message: str,
    director: DirectorAgent,
    log_manager: SequenceAwareLogManager,
    conn,
    channel: str = "telegram",
) -> DirectorReply:
    """One Director reasoning turn, logged under its own pipeline_runs row."""
    run_id = create_run(conn, "director")
    status = "success"
    try:
        with log_manager.task_sequence(
            task_id=str(run_id), description=f"director: {message[:60]}"
        ):
            with log_manager.tool_sequence("director", reason=message[:300]) as ctx:
                reply = director.respond(message)
                ctx.llm_model = reply.model
                ctx.llm_provider = "anthropic"
                ctx.token_count_input = reply.input_tokens
                ctx.token_count_output = reply.output_tokens
                ctx.token_count_cache_create = reply.cache_creation_input_tokens
                ctx.token_count_cache_read = reply.cache_read_input_tokens
                ctx.cost_usd = (
                    compute_cost(
                        reply.model,
                        reply.input_tokens,
                        reply.output_tokens,
                        reply.cache_creation_input_tokens,
                        reply.cache_read_input_tokens,
                    )
                    or 0.0
                )
                ctx.payload = {"channel": channel, "user_message": message[:1000]}
        return reply
    except Exception:
        status = "error"
        raise
    finally:
        complete_run(conn, run_id, status)


def handle(update: Update, director, log_manager, conn) -> str:
    agent, message = route(update.text)
    if agent != "director":
        return (
            f"`/{agent}` isn't wired up in this build yet — only the Director is live. "
            "Talk to me by default, or with `/director`."
        )
    if not message:
        return "I'm here. What do you need?"
    return run_turn(message, director, log_manager, conn, channel="telegram").text


def run_listener(config: DirectorConfig) -> None:
    if not config.telegram_token:
        sys.exit(
            "DIRECTOR_TELEGRAM_TOKEN not set — create a bot via @BotFather and put "
            "the token in .env."
        )
    if config.allowed_user_id is None:
        sys.exit(
            "DIRECTOR_TELEGRAM_ALLOWED_USER not set — refusing to run open to the "
            "world. Set your numeric Telegram user id."
        )

    conn = psycopg.connect(config.postgres_dsn)
    log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
    director = DirectorAgent(
        Anthropic(api_key=config.anthropic_api_key), model=config.model
    )
    tg = TelegramClient(config.telegram_token, timeout=config.poll_timeout)

    log.info("director.listener.start (model=%s)", config.model)
    offset: int | None = None
    while True:
        try:
            updates = tg.get_updates(offset=offset)
        except Exception as exc:  # network blip — back off and retry
            log.warning("getUpdates failed: %s", exc)
            time.sleep(3)
            continue
        for u in updates:
            offset = u.update_id + 1
            if u.user_id != config.allowed_user_id:
                log.warning("ignored message from non-whitelisted user %s", u.user_id)
                continue
            try:
                tg.send_typing(u.chat_id)
                tg.send_message(u.chat_id, handle(u, director, log_manager, conn))
            except Exception as exc:
                log.exception("handler error")
                tg.send_message(u.chat_id, f"Hit an error: {exc}")
