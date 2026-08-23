"""Session-log ingestion — session JSONL -> scout_session_log, two dialects.

One row per meaningful turn: human queries ('query') and assistant text
('progress' mid-loop, 'final' on end_turn). Tool traffic, command echoes, and
system-reminder injections are noise, not narration — skipped. Raw text is
stored verbatim (`text_clean` exists for a later light-cleaning pass; the raw
column is never overwritten — the tidy version must never become the only
version).

Dialects: Claude Code project logs (one dir per project) and Codex CLI rollout
files (the work machine's corpus, shipped via the gdrive: remote into a
month/day tree). Both map onto the same row shape; everything under the Codex
dir uses the Codex reader.

Idempotent: UNIQUE (session_id, turn) + ON CONFLICT DO NOTHING, so re-runs
only append what's new. A session resumed later appends higher line numbers,
which land at the tail of `seq` where the coverage walk will meet them.

Note: the logs live under /root and are 600 — run ingestion as root (the
walk/synthesis stages only need the DB).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime
from pathlib import Path

log = logging.getLogger("uzelhub_crew.scout.ingest")

# A file modified this recently is probably a live session mid-write; skip it
# this pass — the next ingest picks it up whole.
ACTIVE_SESSION_GRACE_SECS = 15 * 60

# Human-turn wrappers that aren't the human speaking.
_SKIP_PREFIXES = ("<command-name>", "<local-command", "<system-reminder>")


def _text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "")
            for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip()
    return ""


def _record_date(rec: dict, fallback: date) -> date:
    ts = rec.get("timestamp")
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    return fallback


def parse_session_file(path: Path) -> list[tuple]:
    """Yield (session_id, session_date, turn, role, turn_type, text) rows."""
    session_id = path.stem
    fallback_date = date.fromtimestamp(path.stat().st_mtime)
    rows: list[tuple] = []
    with path.open(encoding="utf-8", errors="ignore") as fh:
        for turn, line in enumerate(fh):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = rec.get("type")
            msg = rec.get("message") or {}
            if kind == "user":
                text = _text_of(msg.get("content"))
                if not text or text.startswith(_SKIP_PREFIXES):
                    continue
                role, turn_type = "human", "query"
            elif kind == "assistant":
                text = _text_of(msg.get("content"))
                if not text:
                    continue  # tool-use-only round trips carry no narration
                role = "assistant"
                turn_type = "final" if msg.get("stop_reason") == "end_turn" else "progress"
            else:
                continue
            rows.append(
                (session_id, _record_date(rec, fallback_date), turn, role, turn_type, text)
            )
    return rows


def parse_codex_session_file(path: Path) -> list[tuple]:
    """Same row shape from a Codex CLI rollout file (the second dialect).

    The event stream is the clean channel: `user_message` events are exactly
    the human typing (role="user" response_items also carry AGENTS.md /
    environment / turn-abort injections), and `agent_message` events match
    assistant messages one-for-one. Codex has no stop_reason; `task_complete`
    closes a turn, so the agent message it follows is the 'final'.
    """
    session_id = path.stem
    fallback_date = date.fromtimestamp(path.stat().st_mtime)
    rows: list[tuple] = []
    open_assistant: int | None = None  # index in rows, awaiting task_complete
    with path.open(encoding="utf-8", errors="ignore") as fh:
        for turn, line in enumerate(fh):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "event_msg":
                continue
            payload = rec.get("payload") or {}
            kind = payload.get("type")
            if kind == "task_complete":
                if open_assistant is not None:
                    row = rows[open_assistant]
                    rows[open_assistant] = row[:4] + ("final",) + row[5:]
                    open_assistant = None
                continue
            if kind not in ("user_message", "agent_message"):
                continue
            text = (payload.get("message") or "").strip()
            if not text:
                continue
            if kind == "user_message":
                role, turn_type = "human", "query"
            else:
                role, turn_type = "assistant", "progress"
                open_assistant = len(rows)
            rows.append(
                (session_id, _record_date(rec, fallback_date), turn, role, turn_type, text)
            )
    return rows


def ingest(conn, logs_dir: Path, codex_dir: Path | None = None) -> dict[str, int]:
    """Ingest every session JSONL under logs_dir (all project subdirs)."""
    files = [(p, parse_session_file) for p in sorted(logs_dir.glob("*/*.jsonl"))]
    # A secondary source must never take down the primary. `is_dir()` looks
    # like a guard but propagates PermissionError on 3.12 (only ENOENT/ENOTDIR/
    # EBADF/ELOOP are swallowed), so an unreadable codex dir — the ordinary
    # case when ingest runs as anyone but root — aborted the whole run before
    # a single Claude Code session was read. On the one step in this system
    # whose gap is UNRECOVERABLE, that is the wrong failure: session files
    # rotate away, and a permissions problem on the work-machine corpus is no
    # reason to lose the box's own transcripts.
    if codex_dir is not None:
        try:
            if codex_dir.is_dir():
                files += [(p, parse_codex_session_file) for p in sorted(codex_dir.rglob("*.jsonl"))]
        except OSError as exc:
            log.warning("scout.ingest codex dir unreadable (%s) — continuing with session logs only", exc)
    now = time.time()
    stats = {"files": 0, "skipped_active": 0, "rows_seen": 0, "rows_inserted": 0,
             "codex_available": codex_dir is None or any(f[1] is parse_codex_session_file for f in files)}
    for path, parse in files:
        if now - path.stat().st_mtime < ACTIVE_SESSION_GRACE_SECS:
            stats["skipped_active"] += 1
            continue
        rows = parse(path)
        stats["files"] += 1
        stats["rows_seen"] += len(rows)
        if not rows:
            continue
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO scout_session_log
                    (session_id, session_date, turn, role, turn_type, text)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, turn) DO NOTHING
                """,
                rows,
            )
            stats["rows_inserted"] += cur.rowcount or 0
        conn.commit()
    log.info("scout.ingest %s", stats)
    return stats
