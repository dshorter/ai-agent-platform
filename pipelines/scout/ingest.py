"""Session-log ingestion — Claude Code JSONL -> scout_session_log.

One row per meaningful turn: human queries ('query') and assistant text
('progress' mid-loop, 'final' on end_turn). Tool traffic, command echoes, and
system-reminder injections are noise, not narration — skipped. Raw text is
stored verbatim (`text_clean` exists for a later light-cleaning pass; the raw
column is never overwritten — the tidy version must never become the only
version).

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


def ingest(conn, logs_dir: Path) -> dict[str, int]:
    """Ingest every session JSONL under logs_dir (all project subdirs)."""
    files = sorted(logs_dir.glob("*/*.jsonl"))
    now = time.time()
    stats = {"files": 0, "skipped_active": 0, "rows_seen": 0, "rows_inserted": 0}
    for path in files:
        if now - path.stat().st_mtime < ACTIVE_SESSION_GRACE_SECS:
            stats["skipped_active"] += 1
            continue
        rows = parse_session_file(path)
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
