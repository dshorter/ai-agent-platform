"""The mining layer — persist what the walk found.

Jewels used to live in a local list in run.py, get handed to synthesis, and
vanish on process exit; ~1,645 were extracted and lost that way before this
existed (docs/uzelhub-crew/scout-mining-economics.md). Writing them down is
what lets the walk and the synthesis come apart, because a synthesis that can
read jewels from a table no longer has to be the same process that mined them.

Write-side only for now. Selection (the read side `--synthesize` will use)
arrives with the verb split; adding it before there is a caller would be
guessing at its arguments.
"""
from __future__ import annotations

import logging

log = logging.getLogger("uzelhub_crew.scout.jewels")

# The taxonomy the triage prompt asks for. Used to NORMALIZE, never to reject:
# a jewel arriving under an unexpected kind is still a finding, and the note is
# the valuable half. Dropping mined material over a taxonomy mismatch would
# repeat in miniature exactly the loss this table exists to stop.
KNOWN_KINDS = {"principle", "correction", "reframe", "decision", "aha"}
_KIND_MAX = 16  # matches the column; an over-long kind is truncated, not fatal


def _clean_kind(raw: object) -> str:
    kind = str(raw or "").strip().lower()
    if not kind:
        return "unknown"
    if kind not in KNOWN_KINDS:
        # Worth a line in the journal: a persistent unknown kind means the
        # prompt and the taxonomy have drifted apart and one of them is wrong.
        log.info("scout.jewels unexpected kind %r — stored as-is", kind[:_KIND_MAX])
    return kind[:_KIND_MAX]


def persist(
    conn,
    jewels: list[dict],
    rows: list[dict],
    run_id,
    walk_model: str,
) -> int:
    """Write one page's jewels. Returns the number of rows actually inserted.

    `rows` is the page the jewels came from — it supplies both the seq
    allowlist and the session_date, so a hallucinated seq is dropped here
    rather than raising a foreign-key error that would abort the whole pass.
    The walk's other persistence verb (apply_scratchpad) guards the same way
    for the same reason.

    Idempotent by UNIQUE (seq, kind, note): re-walking ore that yields an
    identical finding writes nothing, while a differently-worded finding from
    a later run lands as a new row. Re-mining is meant to accumulate.
    """
    if not jewels:
        return 0
    date_of = {r["seq"]: r["date"] for r in rows}
    inserted = 0
    skipped = 0
    with conn.cursor() as cur:
        for jewel in jewels:
            try:
                seq = int(jewel.get("seq"))
            except (TypeError, ValueError):
                skipped += 1
                continue
            note = str(jewel.get("note", "")).strip()
            if not note or seq not in date_of:
                skipped += 1
                continue
            cur.execute(
                """
                INSERT INTO scout_jewel
                    (seq, kind, note, session_date, run_id, walk_model)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (seq, kind, note) DO NOTHING
                """,
                (seq, _clean_kind(jewel.get("kind")), note, date_of[seq], run_id, walk_model),
            )
            inserted += cur.rowcount or 0
    conn.commit()
    if skipped:
        # Not an error — the triage cites seqs from the page it was shown, so a
        # miss means the model invented one. Counting them makes that visible
        # instead of silent.
        log.info("scout.jewels %d jewel(s) skipped (bad or off-page seq)", skipped)
    return inserted


def select(
    conn,
    since: str | None = None,
    until: str | None = None,
    kinds: list[str] | None = None,
    run_id=None,
    limit: int | None = None,
) -> list[dict]:
    """Read jewels back for a synthesis that did not mine them.

    Returns exactly the shape the walk hands over in-process — {seq, kind,
    note} and nothing more. That sameness is the point: `--pass` and a
    standalone `--synthesize` must put identical context in front of the
    model, or the two paths quietly diverge and the pass stops being the
    thing this was tested against. Anything extra a consumer wants (dates,
    provenance, the turn text itself) is one join away on `seq`.

    Ordered by seq so a selection is deterministic and re-runnable.
    """
    where: list[str] = []
    params: list = []
    if since:
        where.append("session_date >= %s")
        params.append(since)
    if until:
        where.append("session_date <= %s")
        params.append(until)
    if kinds:
        where.append("kind = ANY(%s)")
        params.append(list(kinds))
    if run_id:
        where.append("run_id = %s")
        params.append(run_id)
    sql = "SELECT seq, kind, note FROM scout_jewel"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY seq"
    if limit:
        sql += " LIMIT %s"
        params.append(limit)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [{"seq": s, "kind": k, "note": n} for s, k, n in cur.fetchall()]
