"""
Director listener — the Telegram switchboard + per-message run loop.

Walking skeleton: long-poll Telegram, whitelist Dan, route by slash command
(default -> director), run one reasoning turn, reply, and log the decision to
agent_decisions via the sequence-aware spine.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import date

import psycopg
from anthropic import Anthropic

from agents.director_agent import DirectorAgent, DirectorReply
from pipelines.blog_pipeline.logging_context import (
    DecisionWriter,
    SequenceAwareLogManager,
)
from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.director.config import DirectorConfig
from pipelines.director.project_state import gather_state
from pipelines.director.store import complete_run, create_run
from pipelines.director.telegram import TelegramClient, Update


log = logging.getLogger("uzelhub_crew.director")

# Agents reachable on the shared bot. Only `director` is wired in the walking
# skeleton; the rest are switchboard stubs.
KNOWN_AGENTS = {"director", "sysadmin", "blog"}

# Utility commands the listener answers itself (not routed to an agent). Also
# registered as the bot's "/" autocomplete menu on startup.
BOT_COMMANDS: list[tuple[str, str]] = [
    ("brief", "Run the morning brief now"),
    ("director", "Message the Director (bare text works too)"),
    ("help", "List commands"),
]


def help_text() -> str:
    lines = "\n".join(f"/{name} — {desc}" for name, desc in BOT_COMMANDS)
    stubs = ", ".join(f"/{a}" for a in sorted(KNOWN_AGENTS - {"director"}))
    return (
        f"Commands:\n{lines}\n\n"
        f"Bare text goes to the Director. ({stubs} are reserved for agents "
        "not wired up yet.)"
    )


def route(text: str) -> tuple[str, str]:
    """(agent, message). A leading /agent slash-command routes; bare text -> director."""
    stripped = text.strip()
    if stripped.startswith("/"):
        head, _, rest = stripped[1:].partition(" ")
        if head.lower() in KNOWN_AGENTS:
            return head.lower(), rest.strip()
    return "director", stripped


# Recent-conversation memory: replay the last N turns back to the Director so a
# thread feels continuous. Bounded (turns + per-reply chars) to keep tokens sane;
# DIRECTOR_HISTORY_TURNS=0 disables it. Only possible because slice 1 now persists
# the Director's replies — before that there was nothing to replay.
RECENT_HISTORY_TURNS = int(os.environ.get("DIRECTOR_HISTORY_TURNS", "6"))
HISTORY_REPLY_CAP = 1200  # chars of each past reply fed back as context


def load_recent_history(conn, channel: str, limit: int = RECENT_HISTORY_TURNS):
    """Last `limit` (user, reply) turns on this channel, oldest-first, as messages."""
    if limit <= 0:
        return []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT decision_payload->>'user_message',
                   decision_payload->>'director_reply'
            FROM agent_decisions
            WHERE agent_name = 'director'
              AND decision_payload->>'channel' = %s
              AND decision_payload->>'director_reply' IS NOT NULL
              AND decision_payload->>'director_reply' <> ''
            ORDER BY decision_timestamp DESC
            LIMIT %s
            """,
            (channel, limit),
        )
        rows = cur.fetchall()
    messages: list[dict[str, str]] = []
    for user_message, director_reply in reversed(rows):
        if not user_message or not director_reply:
            continue
        messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": director_reply[:HISTORY_REPLY_CAP]})
    return messages


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
                history = load_recent_history(conn, channel)  # recent-turn memory
                state = gather_state()  # the Director's eyes: read project state fresh
                reply = director.respond(message, history=history, context=state)
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
                ctx.payload = {
                    "channel": channel,
                    "user_message": message[:1000],
                    "director_reply": reply.text,  # persist the output — no more evaporation
                    "saw_project_state": bool(state),
                    "history_turns": len(history) // 2,
                    "iterations": reply.iterations,
                    "tool_calls": reply.tool_calls,  # what it read this turn — the trace
                    # None when it finished on its own; the cap's name when one cut
                    # it off. Queryable, so a forced close is a fact in the spine
                    # rather than something you have to read the reply to notice.
                    "limit_hit": reply.limit_hit,
                }
        return reply
    except Exception:
        status = "error"
        raise
    finally:
        complete_run(conn, run_id, status)


def handle(update: Update, director, log_manager, conn) -> str:
    stripped = update.text.strip()
    if stripped.startswith("/"):
        head, _, rest = stripped[1:].partition(" ")
        cmd = head.split("@", 1)[0].lower()  # groups append @botname; harmless in 1:1
        if cmd in ("help", "start"):  # Telegram clients auto-send /start on first open
            return help_text()
        if cmd == "brief":
            from pipelines.director.tick import TICKS  # lazy: tick.py imports run_turn from here

            name = (rest.strip() or "morning").lower()
            if name not in TICKS:
                return f"Unknown brief {name!r} — known: {', '.join(sorted(TICKS))}."
            header, prompt = TICKS[name]
            # channel="telegram" (not tick:*) so the brief lands in this thread's
            # replayed history and follow-up questions can refer to it.
            reply = run_turn(prompt, director, log_manager, conn, channel="telegram")
            return f"{header} — {date.today():%a %b %-d}\n\n{reply.text}"
    agent, message = route(update.text)
    if agent != "director":
        return (
            f"`/{agent}` isn't wired up in this build yet — only the Director is live. "
            "Talk to me by default, or with `/director`."
        )
    if not message:
        return "I'm here. What do you need?"
    return run_turn(message, director, log_manager, conn, channel="telegram").text


def _connect_db(config: DirectorConfig):
    """The long-lived connection + the spine writer bound to it. Rebuilt
    whenever Postgres bounces: on 2026-07-13 a clean container restart left
    the old socket dead, and every turn failed (AdminShutdown, then "the
    connection is closed") until the process was kicked — the error surfaces
    lazily on first use, so reconnect must too."""
    conn = psycopg.connect(config.postgres_dsn)
    return conn, SequenceAwareLogManager(db_writer=DecisionWriter(conn))


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

    conn, log_manager = _connect_db(config)
    director = DirectorAgent(
        Anthropic(api_key=config.anthropic_api_key),
        model=config.model,
        max_cost_usd=config.max_cost_usd,
    )
    tg = TelegramClient(config.telegram_token, timeout=config.poll_timeout)
    tg.set_my_commands(BOT_COMMANDS)  # register the "/" autocomplete menu

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
                if conn.closed:  # died while idle — rebuild before the turn
                    conn, log_manager = _connect_db(config)
                try:
                    reply = handle(u, director, log_manager, conn)
                except psycopg.Error:
                    log.warning("db connection lost — reconnecting")
                    try:
                        conn.close()
                    except Exception:
                        pass
                    conn, log_manager = _connect_db(config)
                    reply = handle(u, director, log_manager, conn)  # one retry
                tg.send_message(u.chat_id, reply)
            except Exception as exc:
                log.exception("handler error")
                tg.send_message(u.chat_id, f"Hit an error: {exc}")
