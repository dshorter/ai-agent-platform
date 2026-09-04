"""Tests for the jewel write path — the layer that stops the mining evaporating.

Two things are guarded here, because both fail silently rather than loudly.

The GUARDS: the triage is a model, so it can cite a seq that wasn't on the page
it was shown. Unguarded that is a foreign-key error mid-pass, which aborts the
whole transaction and loses the good jewels alongside the bad one. `persist`
drops off-page seqs instead, and the count it returns is what tells anyone the
drop happened.

The SQL: the ON CONFLICT key is what makes re-mining accumulate rather than
duplicate. Get it wrong in either direction and the damage is quiet — too
strict silently discards real second-run findings, too loose fills the table
with copies of the first run. The DB-backed test exercises the real statement
against the real constraint; everything else here runs without a database.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.scout.jewels import KNOWN_KINDS, _clean_kind, persist  # noqa: E402


# --- the page a walk was shown -------------------------------------------------

ROWS = [
    {"seq": 100, "date": "2026-06-01"},
    {"seq": 101, "date": "2026-06-01"},
    {"seq": 102, "date": "2026-06-02"},
]


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.sql: str = ""
        self.rowcount = 1

    def execute(self, sql, params):
        self.sql = sql
        self.calls.append(params)

    def field(self, call_index: int, column: str):
        """The value written to a NAMED column.

        Positional assertions on these params were fragile, and it bit on
        2026-09-03: adding `source_ref` as the second column shifted everything
        after it, so one test failed loudly and the rest kept passing while
        checking a different value than their name claimed. Read by column name
        off the statement itself instead — then a column added anywhere is
        invisible to every test that does not care about it."""
        cols = [c.strip() for c in
                self.sql.split("(", 1)[1].split(")", 1)[0].split(",")]
        return self.calls[call_index][cols.index(column)]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self) -> None:
        self.cur = FakeCursor()
        self.commits = 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1


def test_kind_normalizes_but_never_rejects():
    assert _clean_kind("  PRINCIPLE ") == "principle"
    for k in KNOWN_KINDS:
        assert _clean_kind(k) == k
    # An unexpected kind is still a finding — kept, not dropped.
    assert _clean_kind("epiphany") == "epiphany"
    assert _clean_kind(None) == "unknown"
    # Over-long kinds are truncated to the column, never fatal.
    assert len(_clean_kind("a" * 40)) == 16


def test_offpage_and_malformed_seqs_are_dropped_not_raised():
    conn = FakeConn()
    written = persist(
        conn,
        [
            {"seq": 100, "kind": "principle", "note": "on the page"},
            {"seq": 999, "kind": "aha", "note": "seq the model invented"},
            {"seq": "not-an-int", "kind": "aha", "note": "unparseable"},
            {"seq": 101, "kind": "aha", "note": "   "},          # empty note
            {"seq": 102, "kind": "decision", "note": "also fine"},
        ],
        ROWS,
        run_id="11111111-1111-1111-1111-111111111111",
        walk_model="claude-haiku-4-5-20251001",
    )
    assert written == 2
    assert [conn.cur.field(i, "seq") for i in (0, 1)] == [100, 102]


def test_session_date_comes_from_the_page_not_the_model():
    conn = FakeConn()
    persist(
        conn,
        [{"seq": 102, "kind": "aha", "note": "n", "session_date": "1999-01-01"}],
        ROWS,
        run_id="11111111-1111-1111-1111-111111111111",
        walk_model="m",
    )
    # The ore row is the authority on when a turn happened.
    assert conn.cur.field(0, "session_date") == "2026-06-02"


def test_transcript_jewels_anchor_on_seq_and_leave_source_ref_null():
    """The jewel_anchor_matches_type CHECK rejects a transcript row that
    carries a source_ref, so the write path has to get this right before the
    database sees it — a violation here would abort a whole page."""
    conn = FakeConn()
    persist(
        conn,
        [{"seq": 100, "kind": "aha", "note": "n"}],
        ROWS,
        run_id="11111111-1111-1111-1111-111111111111",
        walk_model="m",
    )
    assert conn.cur.field(0, "source_type") == "transcript"
    assert conn.cur.field(0, "source_ref") is None
    assert conn.cur.field(0, "seq") == 100


def test_empty_input_touches_nothing():
    conn = FakeConn()
    assert persist(conn, [], ROWS, run_id="x", walk_model="m") == 0
    assert conn.commits == 0


# --- the real statement, against the real constraint ---------------------------


def _live_conn():
    """A connection to the dev database, or None. These tests are additive:
    the logic above runs everywhere, this pair runs where a DB exists."""
    try:
        import psycopg
    except ImportError:  # pragma: no cover
        return None
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return None
    dsn = next(
        (l.split("=", 1)[1].strip() for l in env.read_text().splitlines()
         if l.startswith("POSTGRES_DSN=")),
        None,
    )
    if not dsn:
        return None
    try:
        return psycopg.connect(dsn, connect_timeout=3)
    except Exception:  # pragma: no cover — no DB in this environment
        return None


_TEST_RUN = "scout-test"


@pytest.fixture
def live():
    """A connection plus explicit teardown.

    NOT a rollback fixture, deliberately: `persist` commits, the same way
    `walk.apply_scratchpad` does, because a pass that dies mid-walk should keep
    the pages it already mined. So the transaction is gone before the test can
    roll anything back, and cleanup has to name what it created. Written the
    rollback way first, this leaked three rows into the live table and made the
    NEXT run of the suite fail — which is the honest argument for doing it this
    way round."""
    conn = _live_conn()
    if conn is None:
        pytest.skip("no database reachable")
    try:
        yield conn
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM scout_jewel WHERE run_id IN "
                    "(SELECT run_id FROM pipeline_runs WHERE pipeline_name = %s)",
                    (_TEST_RUN,),
                )
                cur.execute(
                    "DELETE FROM pipeline_runs WHERE pipeline_name = %s", (_TEST_RUN,)
                )
            conn.commit()
        finally:
            conn.close()


def test_conflict_key_makes_re_mining_idempotent_but_not_lossy(live):
    with live.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_runs (pipeline_name, status) "
            "VALUES (%s, 'running') RETURNING run_id",
            (_TEST_RUN,),
        )
        run_id = cur.fetchone()[0]
        cur.execute("SELECT seq, session_date FROM scout_session_log ORDER BY seq LIMIT 2")
        ore = [{"seq": s, "date": d} for s, d in cur.fetchall()]
    live.commit()  # the FK must be visible to persist's own transaction
    assert len(ore) == 2, "ore is empty — nothing to test against"

    jewel = {"seq": ore[0]["seq"], "kind": "principle", "note": "a finding"}

    assert persist(live, [jewel], ore, run_id, "m1") == 1
    # Same run, same finding, verbatim: idempotent.
    assert persist(live, [jewel], ore, run_id, "m1") == 0
    # A later run wording it differently is NEW material, not a duplicate —
    # this is the half a stricter key would silently destroy.
    reworded = dict(jewel, note="the same finding, said another way")
    assert persist(live, [reworded], ore, run_id, "m1") == 1
    # A different kind on the same turn is also its own row.
    assert persist(live, [dict(jewel, kind="aha")], ore, run_id, "m1") == 1

    with live.cursor() as cur:
        cur.execute("SELECT count(*) FROM scout_jewel WHERE run_id = %s", (run_id,))
        assert cur.fetchone()[0] == 3


def test_table_carries_no_disposition_column(live):
    """The pineapple rule, enforced structurally. If a column ever appears that
    records what became of a jewel, the Scout can be filtered by editor
    outcomes and the no-backpropagation guarantee is gone. Cheaper to fail a
    test than to notice in six months."""
    with live.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'scout_jewel'"
        )
        cols = {r[0] for r in cur.fetchall()}
    forbidden = {"lead_id", "became_lead", "status", "score", "verdict",
                 "published", "claimed", "spiked", "disposition"}
    assert not (cols & forbidden), f"disposition column(s) on scout_jewel: {cols & forbidden}"


def test_select_returns_the_same_shape_the_walk_hands_over(live):
    """`--pass` feeds synthesis its in-memory jewels; `--synthesize` feeds it
    rows from this table. If the two shapes drift, the standalone verb stops
    being the thing the daily pass was tested against — so select() returns
    {seq, kind, note} and nothing else, on purpose."""
    from pipelines.scout.jewels import select

    with live.cursor() as cur:
        cur.execute(
            "INSERT INTO pipeline_runs (pipeline_name, status) "
            "VALUES (%s, 'running') RETURNING run_id",
            (_TEST_RUN,),
        )
        run_id = cur.fetchone()[0]
        cur.execute("SELECT seq, session_date FROM scout_session_log ORDER BY seq LIMIT 2")
        ore = [{"seq": s, "date": d} for s, d in cur.fetchall()]
    live.commit()

    persist(
        live,
        [
            {"seq": ore[0]["seq"], "kind": "principle", "note": "first"},
            {"seq": ore[1]["seq"], "kind": "aha", "note": "second"},
        ],
        ore,
        run_id,
        "m1",
    )

    got = select(live, run_id=run_id)
    # The shape must match what the walk hands synthesis in-process. Since 1.4.0
    # that includes the provenance pair, because a non-transcript jewel has no
    # seq and would otherwise arrive with nothing the model could cite.
    assert [set(j) for j in got] == [
        {"seq", "source_type", "source_ref", "kind", "note"}] * 2
    assert [j["seq"] for j in got] == sorted(j["seq"] for j in got), "must be ore-ordered"
    assert all(j["source_type"] == "transcript" and j["source_ref"] is None
               for j in got), "a transcript jewel anchors on seq alone"

    # Facets narrow, and an empty selection is empty rather than everything —
    # a filter that silently falls back to the whole table would hand a
    # monthly digest the entire corpus.
    assert len(select(live, run_id=run_id, kinds=["aha"])) == 1
    assert select(live, run_id=run_id, since="2099-01-01") == []
    assert len(select(live, run_id=run_id, limit=1)) == 1
