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


def candidate_index(rows: list[dict], source_type: str) -> dict:
    """The allowlist: every anchor the walker was actually shown, → its date.

    Transcript pages key on `seq`; every other source keys on `ref`. Both come
    from the candidate set the reader handed the model, which is the whole point
    — see `resolve_anchor`."""
    if source_type == "transcript":
        return {int(r["seq"]): r["date"] for r in rows}
    return {str(r["ref"]): r["date"] for r in rows}


def resolve_anchor(jewel: dict, source_type: str, index: dict):
    """(anchor, date) if this jewel cites something it was shown, else None.

    **This function is the anti-hallucination control for non-transcript
    sources.** Transcript jewels have a second line of defence — `seq` is a
    foreign key, so a fabricated one would be rejected by Postgres even if this
    check were removed. A git sha or a file path has no table to reference, so
    for those sources this is the ONLY thing standing between a model's
    invention and a persisted row. Schema 1.4.0 gave up the FK for five of six
    sources deliberately; this is what it was traded for.
    """
    if source_type == "transcript":
        try:
            anchor = int(jewel.get("seq"))
        except (TypeError, ValueError):
            return None
    else:
        anchor = str(jewel.get("ref", "")).strip()
        if not anchor:
            return None
    if anchor not in index:
        return None
    return anchor, index[anchor]


def persist(
    conn,
    jewels: list[dict],
    rows: list[dict],
    run_id,
    walk_model: str,
    source_type: str = "transcript",
) -> int:
    """Write one page's jewels. Returns the number of rows actually inserted.

    `rows` is the candidate set the jewels came from — it supplies both the
    anchor allowlist and the date, so a hallucinated citation is dropped here
    rather than raising a foreign-key error that would abort the whole pass.
    The walk's other persistence verb (apply_scratchpad) guards the same way
    for the same reason.

    `source_type` defaults to `transcript` so existing callers are unchanged.
    A reader for another source passes its own type and puts `ref` on each
    candidate row instead of `seq`; the anchor then lands in `source_ref` and
    `seq` stays NULL, which is what the `jewel_anchor_matches_type` CHECK
    requires. The value is written explicitly rather than left to the column
    DEFAULT, because it belongs at the call site where it is true.

    The ON CONFLICT target is deliberately bare. Schema 1.4.0 replaced
    UNIQUE (seq, kind, note) with a unique index over
    (source_type, COALESCE(seq::text, source_ref), kind, note), because a
    nullable seq under the old constraint would have made every non-transcript
    jewel trivially unique. Naming that expression as an inference target here
    would couple this INSERT to the index's exact expression text; the bare form
    resolves against whatever unique constraint the row actually violates.

    Idempotent by that index: re-walking ore that yields an
    identical finding writes nothing, while a differently-worded finding from
    a later run lands as a new row. Re-mining is meant to accumulate.
    """
    if not jewels:
        return 0
    index = candidate_index(rows, source_type)
    is_transcript = source_type == "transcript"
    inserted = 0
    skipped = 0
    with conn.cursor() as cur:
        for jewel in jewels:
            note = str(jewel.get("note", "")).strip()
            resolved = resolve_anchor(jewel, source_type, index)
            if not note or resolved is None:
                skipped += 1
                continue
            anchor, when = resolved
            cur.execute(
                """
                INSERT INTO scout_jewel
                    (seq, source_ref, kind, note, session_date, run_id,
                     walk_model, source_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (
                    anchor if is_transcript else None,
                    None if is_transcript else anchor,
                    _clean_kind(jewel.get("kind")),
                    note,
                    when,
                    run_id,
                    walk_model,
                    source_type,
                ),
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
    source_types: list[str] | None = None,
) -> list[dict]:
    """Read jewels back for a synthesis that did not mine them.

    Returns the shape the walk hands over in-process. That sameness is the
    point: `--pass` and a standalone `--synthesize` must put identical context
    in front of the model, or the two paths quietly diverge and the pass stops
    being the thing this was tested against. Anything extra a consumer wants
    (dates, run provenance, the turn text itself) is one join away.

    **`source_type` and `source_ref` are carried, added 2026-09-04.** Schema
    1.4.0 let a jewel anchor to a non-transcript source, and this function was
    left behind — it selected `seq` alone, so a git- or doc-anchored jewel would
    have reached synthesis with `seq` NULL and *no citable anchor at all*, while
    the prompt still told the model its jewels cite seqs. Not a live fault yet
    (no reader produces one), but it would have become one the moment the first
    reader landed, which is exactly how the `ON CONFLICT` break happened: one
    side of the change migrated, the other not.

    **`source_types` filters on provenance, added 2026-09-04.** It is what makes
    the two experiments the estate owes itself separable, and it costs one
    `WHERE` clause because 1.4.0 already made `source_type` a column.

    Two variables were about to move together: synthesis dropped Fable → Sonnet
    on 2026-09-03, and the source mix is about to change from transcript-only to
    six sources. If both move at once a better lead list is uninterpretable —
    the mix may have done the work while the cheap model coasted, or the cheap
    model may have cost depth the richer sources masked. That would burn the A/B
    open since 2026-07-26 rather than settle it (ADR-002 §6b).

    With this filter both questions become controlled comparisons over jewels
    already on disk, mining nothing and costing one synthesis call per arm:

        --source-type transcript   vs   (no filter)      # does the mix help?
        SCOUT_SYNTHESIS_MODEL=A     vs   =B              # is Fable worth 5x?

    Run BOTH ARMS WITH `--dry-run`. Synthesis reads the already-pitched payload
    from the ledger at run time, so a live first arm files leads that the second
    arm is then instructed not to duplicate — which makes the second arm
    structurally unable to surface the first arm's best material, and the
    deficit reads as a quality difference. Dry runs file nothing.

    Ordering is chronological and total. Plain `ORDER BY seq` degrades once seq
    is nullable — Postgres sorts NULLs last, so every non-transcript jewel would
    pile up at the end of an otherwise time-ordered selection regardless of when
    its material dates from. `session_date` first restores the ore's own
    chronology across all sources; `id` last keeps it deterministic and
    re-runnable when two rows tie.
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
    if source_types:
        where.append("source_type = ANY(%s)")
        params.append(list(source_types))
    sql = "SELECT seq, source_type, source_ref, kind, note FROM scout_jewel"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY session_date, seq NULLS LAST, source_ref, id"
    if limit:
        sql += " LIMIT %s"
        params.append(limit)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [
            {"seq": s, "source_type": st, "source_ref": sr, "kind": k, "note": n}
            for s, st, sr, k, n in cur.fetchall()
        ]
