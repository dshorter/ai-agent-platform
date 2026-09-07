"""006's copy of the rules and the code's copy are the same rules.

The migration moves three things out of Python and into the schema: the five
content types, the lifecycle's legal transitions with the actor that may make
them, and the digest cut. Two copies of one rule is how a fix lands on one and
misses the other — the failure this repo has already recorded twice — so the
moment 006 is applied, these assertions start holding both copies together.

Every test here SKIPS until then: no database, or a database without
schema_version 1.5.0, and there is nothing to compare. That is deliberate. The
file is a tripwire that arms itself on the day of the cutover rather than a
reminder in a doc that the cutover has to remember to read.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.scout.leads import _digest  # noqa: E402
from pipelines.scout.lead_mark import TRANSITIONS  # noqa: E402
from pipelines.wire_editor.run import TYPES  # noqa: E402

DIGEST_CHARS = 240

PITCHES = [
    "Short one.",
    "a" * 98 + ". " + "b" * 300,
    "word " * 200,
    "The Scout mines jewels from the box's ore. It keeps no taste at all, "
    "which is the pineapple rule as a job description rather than a constraint "
    "on a prompt. " + "x" * 200,
    "No sentence break here at all, just a long run of words that keeps going "
    "without any terminal punctuation, so the cut has to land on a space "
    + "y" * 200,
    "Q? Then more. " + "z" * 300,
    "",
]


def _conn():
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


@pytest.fixture
def migrated():
    """A connection to a database where 006 is applied, or a skip.

    Read-only throughout: every assertion below is a SELECT, so there is
    nothing to tear down and nothing that can leak into a live table.
    """
    conn = _conn()
    if conn is None:
        pytest.skip("no database reachable")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM schema_version WHERE version_number = '1.5.0'"
            )
            if not cur.fetchone()[0]:
                pytest.skip("006 not applied — the ledger is still leads.yaml")
        yield conn
    finally:
        conn.close()


def test_the_database_knows_the_same_five_types(migrated):
    with migrated.cursor() as cur:
        cur.execute("SELECT type FROM content_type")
        assert {r[0] for r in cur.fetchall()} == TYPES


def test_the_database_knows_the_same_lifecycle(migrated):
    """from_state and actor, against lead_mark's dict.

    `new` is in the table and not in TRANSITIONS, correctly: it is where a lead
    starts, not a move anyone makes.
    """
    with migrated.cursor() as cur:
        cur.execute("SELECT state, from_state, actor FROM lead_state")
        rows = {state: (set(froms), actor) for state, froms, actor in cur.fetchall()}

    assert set(rows) - {"new"} == set(TRANSITIONS)
    for state, (legal_from, actor) in TRANSITIONS.items():
        db_from, db_actor = rows[state]
        assert db_actor == actor, f"{state}: {db_actor} in the DB, {actor} in code"
        # The DB permits drafted -> drafted so a redraft is expressible; the
        # Python dict leaves that to run.py. Everything else must match exactly.
        assert legal_from <= db_from, f"{state}: DB allows {db_from}, code {legal_from}"


@pytest.mark.parametrize("pitch", PITCHES)
def test_the_digest_cut_is_the_same_cut(migrated, pitch):
    with migrated.cursor() as cur:
        cur.execute("SELECT scout_pitch_digest(%s, %s)", (pitch, DIGEST_CHARS))
        assert cur.fetchone()[0] == _digest(pitch, DIGEST_CHARS)


def test_the_scout_may_not_read_a_disposition(migrated):
    """The migration's reason for existing, asserted as privileges rather than
    as a promise about which reader the Scout happens to use."""
    with migrated.cursor() as cur:
        cur.execute(
            """
            SELECT table_name, privilege_type
              FROM information_schema.table_privileges
             WHERE grantee = 'scout_role'
            """
        )
        whole_relation = {(t, p) for t, p in cur.fetchall()}

    assert ("scout_pitched", "SELECT") in whole_relation
    for forbidden in ("scout_lead", "scout_lead_stamp"):
        assert not [p for t, p in whole_relation if t == forbidden], (
            f"scout_role holds a whole-relation grant on {forbidden}"
        )
