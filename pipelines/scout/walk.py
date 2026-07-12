"""The coverage walk — forward-only, cursor-keyed, logs ONLY.

The cursor guarantees the append-only log import gets fully read at least
once. It encodes read position, never taste; it lives in the state dir as
plain JSON — external, inspectable, warm-bootable. Reset (delete the file) to
re-scan. Keyset on `seq` (WHERE seq > cursor), never OFFSET.

Scratchpad writes append — the raw text column is never touched, and nothing
downstream parses the scratchpad (it's the Scout's own opaque space).
"""
from __future__ import annotations

import json
from pathlib import Path

# Per-row clip for the triage prompt: enough to catch a jewel, small enough
# that a page of rows stays a cheap call. The full text stays in the DB.
ROW_CLIP_CHARS = 1200


def load_cursor(state_dir: Path) -> int:
    path = state_dir / "cursor.json"
    if path.exists():
        return int(json.loads(path.read_text()).get("seq", 0))
    return 0


def save_cursor(state_dir: Path, seq: int) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "cursor.json").write_text(json.dumps({"seq": seq}) + "\n")


def fetch_page(conn, after_seq: int, limit: int) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT seq, session_id, session_date, turn, role, turn_type, text
            FROM scout_session_log
            WHERE seq > %s
            ORDER BY seq
            LIMIT %s
            """,
            (after_seq, limit),
        )
        return [
            {
                "seq": seq,
                "session_id": sid,
                "date": str(sdate),
                "turn": turn,
                "role": role,
                "turn_type": ttype,
                "text": text,
            }
            for seq, sid, sdate, turn, role, ttype, text in cur.fetchall()
        ]


def page_as_prompt(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        text = r["text"]
        if len(text) > ROW_CLIP_CHARS:
            text = text[:ROW_CLIP_CHARS] + " …(clipped)"
        lines.append(
            f"[seq={r['seq']} session={r['session_id'][:8]} {r['date']} "
            f"turn={r['turn']} {r['role']}/{r['turn_type']}]\n{text}"
        )
    return "\n\n".join(lines)


def apply_scratchpad(conn, notes: list[dict], valid_seqs: set[int]) -> int:
    """Append triage notes to rows' scratchpad. Appends only; raw text untouched."""
    applied = 0
    with conn.cursor() as cur:
        for note in notes:
            try:
                seq = int(note.get("seq"))
            except (TypeError, ValueError):
                continue
            text = str(note.get("note", "")).strip()
            if not text or seq not in valid_seqs:
                continue
            cur.execute(
                """
                UPDATE scout_session_log
                SET scratchpad = COALESCE(scratchpad || E'\n', '') || %s
                WHERE seq = %s
                """,
                (text, seq),
            )
            applied += cur.rowcount or 0
    conn.commit()
    return applied


def append_map_notes(state_dir: Path, notes: list[str], stamp: str) -> None:
    """The navigation map — where things live, which sources run rich. All
    navigation, no taste (the pineapple rule)."""
    if not notes:
        return
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "map.md"
    with path.open("a", encoding="utf-8") as fh:
        for note in notes:
            fh.write(f"- {stamp}: {note.strip()}\n")


def read_map(state_dir: Path, max_chars: int = 4000) -> str:
    path = state_dir / "map.md"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    return text[-max_chars:]  # most recent navigation notes
