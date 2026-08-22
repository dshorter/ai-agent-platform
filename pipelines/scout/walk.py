"""The coverage walk — forward-only, cursor-keyed, logs ONLY.

TWO cursors, both in the state dir as plain JSON — external, inspectable,
warm-bootable. `forward` guarantees the append-only log import gets fully read
at least once and only ever moves ahead. `backfill` re-walks from the start so
ore skimmed under the old oversized plate can be mined properly; it is a
separate position precisely so re-mining can never rewind coverage of what is
new. Both encode read position, never taste. Keyset on `seq` (WHERE seq >
cursor), never OFFSET.

Scratchpad writes append — the raw text column is never touched, and nothing
downstream parses the scratchpad (it's the Scout's own opaque space).
"""
from __future__ import annotations

import json
from pathlib import Path

# Per-row clip for the triage prompt: enough to catch a jewel, small enough
# that a page of rows stays a cheap call. The full text stays in the DB.
ROW_CLIP_CHARS = 1200


def load_cursors(state_dir: Path) -> dict:
    """Both read positions: {"forward": int, "backfill": int}.

    `forward` is the original guarantee — the append-only log gets read at
    least once — and only ever moves ahead. `backfill` is the re-mining
    position, walking from 0 back up toward wherever forward stood, so ore
    that was skimmed under the old 450-row plate can be worked properly
    without disturbing coverage of what is new.

    Reads the pre-2026-08 single-cursor shape ({"seq": N}) as forward, so an
    existing state file keeps working and stays hand-inspectable — the whole
    point of the cursor living outside the database.
    """
    path = state_dir / "cursor.json"
    if not path.exists():
        return {"forward": 0, "backfill": 0}
    raw = json.loads(path.read_text())
    if "seq" in raw and "forward" not in raw:
        return {"forward": int(raw["seq"]), "backfill": 0}
    return {
        "forward": int(raw.get("forward", 0)),
        "backfill": int(raw.get("backfill", 0)),
    }


def save_cursors(state_dir: Path, forward: int | None = None, backfill: int | None = None) -> None:
    """Write one or both positions, preserving the other.

    Never blind-writes the whole file: a pass that only advanced forward must
    not reset backfill to whatever it happened to read at start, and vice
    versa.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    cur = load_cursors(state_dir)
    if forward is not None:
        cur["forward"] = forward
    if backfill is not None:
        cur["backfill"] = backfill
    (state_dir / "cursor.json").write_text(json.dumps(cur) + "\n")


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
