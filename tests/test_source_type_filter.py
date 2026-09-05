"""--source-type on --synthesize: the filter that keeps two experiments apart.

Synthesis dropped Fable -> Sonnet on 2026-09-03 and the source mix is about to
change from transcript-only to six sources. Moving both at once makes a better
lead list uninterpretable and burns the A/B open since 2026-07-26 (ADR-002 6b).
This filter is what makes each question a controlled comparison over jewels
already on disk.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.scout.jewels import select  # noqa: E402


class FakeCursor:
    """Captures the statement rather than running it — this test is about the
    WHERE clause that gets built, not about Postgres."""

    def __init__(self):
        self.sql, self.params = "", []

    def execute(self, sql, params):
        self.sql, self.params = sql, params

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self):
        self.cur = FakeCursor()

    def cursor(self):
        return self.cur


def _run(**kw):
    c = FakeConn()
    select(c, **kw)
    return c.cur


def test_no_filter_selects_every_source():
    """The default must stay 'all sources' — a filter that defaults to
    transcripts would re-create the constraint 1.4.0 was written to remove."""
    cur = _run()
    assert "source_type" not in cur.sql.split("FROM")[1]
    assert cur.params == []


def test_one_source_type_becomes_an_any_clause():
    cur = _run(source_types=["transcript"])
    assert "source_type = ANY(%s)" in cur.sql
    assert cur.params == [["transcript"]]


def test_source_type_is_repeatable():
    """Arm B of the mix experiment is 'everything except transcripts', which is
    expressed by naming the others rather than by a NOT."""
    cur = _run(source_types=["git", "doc", "agent_decisions"])
    assert cur.params == [["git", "doc", "agent_decisions"]]


def test_it_composes_with_the_other_selectors():
    """An arm holds period AND mix constant at once, or it is not a control."""
    cur = _run(since="2026-06-01", until="2026-06-30",
               kinds=["principle"], source_types=["git"])
    where = cur.sql.split("WHERE")[1].split("ORDER BY")[0]
    for clause in ("session_date >= %s", "session_date <= %s",
                   "kind = ANY(%s)", "source_type = ANY(%s)"):
        assert clause in where
    assert cur.params == ["2026-06-01", "2026-06-30", ["principle"], ["git"]]


def test_empty_list_is_not_a_filter():
    """`--source-type` absent parses to None; an empty list must behave the
    same rather than producing `= ANY('{}')`, which matches nothing and would
    silently return an empty selection."""
    assert _run(source_types=[]).params == []


def test_ordering_survives_the_filter():
    """Non-transcript jewels sort by the ore's own date, not last."""
    assert "ORDER BY session_date, seq NULLS LAST" in _run(source_types=["git"]).sql
