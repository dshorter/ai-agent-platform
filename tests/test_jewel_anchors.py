"""Tests for the jewel anchor allowlist — the anti-hallucination control.

For transcripts this is belt-and-braces: `seq` is a foreign key, so Postgres
would reject a fabricated one anyway. For every other source there is no FK to
fall back on, so `resolve_anchor` is the ONLY thing between a model's invention
and a persisted row. Schema 1.4.0 traded the FK away for five of six sources on
the understanding that this exists and is tested.

    .venv/bin/python -m pytest tests/test_jewel_anchors.py -q
"""
from __future__ import annotations

from datetime import date

from pipelines.scout.jewels import candidate_index, resolve_anchor

DAY = date(2026, 9, 3)
PAGE = [{"seq": 41, "date": DAY}, {"seq": 42, "date": DAY}]
COMMITS = [{"ref": "abc1234", "date": DAY}, {"ref": "def5678", "date": DAY}]


# ── transcripts ──────────────────────────────────────────────────────────────

def test_transcript_seq_on_the_page_resolves():
    idx = candidate_index(PAGE, "transcript")
    assert resolve_anchor({"seq": 41}, "transcript", idx) == (41, DAY)


def test_transcript_seq_off_the_page_is_refused():
    # The model citing a seq it was never shown is the hallucination case.
    idx = candidate_index(PAGE, "transcript")
    assert resolve_anchor({"seq": 999}, "transcript", idx) is None


def test_transcript_seq_as_a_string_still_resolves():
    # Models return JSON; a numeric string is not a fabrication.
    idx = candidate_index(PAGE, "transcript")
    assert resolve_anchor({"seq": "42"}, "transcript", idx) == (42, DAY)


def test_transcript_missing_or_junk_seq_is_refused():
    idx = candidate_index(PAGE, "transcript")
    for bad in ({}, {"seq": None}, {"seq": "not-a-number"}, {"ref": "abc1234"}):
        assert resolve_anchor(bad, "transcript", idx) is None


# ── every other source ───────────────────────────────────────────────────────

def test_git_ref_in_the_candidate_set_resolves():
    idx = candidate_index(COMMITS, "git")
    assert resolve_anchor({"ref": "abc1234"}, "git", idx) == ("abc1234", DAY)


def test_invented_git_ref_is_refused():
    # No FK exists for a sha. This assertion is the whole guarantee.
    idx = candidate_index(COMMITS, "git")
    assert resolve_anchor({"ref": "0000000"}, "git", idx) is None


def test_git_ref_is_whitespace_trimmed_not_fuzzy_matched():
    idx = candidate_index(COMMITS, "git")
    assert resolve_anchor({"ref": "  abc1234  "}, "git", idx) == ("abc1234", DAY)
    # A prefix is NOT the same commit — refuse rather than guess.
    assert resolve_anchor({"ref": "abc"}, "git", idx) is None


def test_empty_or_missing_ref_is_refused():
    idx = candidate_index(COMMITS, "git")
    for bad in ({}, {"ref": ""}, {"ref": "   "}, {"seq": 41}):
        assert resolve_anchor(bad, "git", idx) is None


def test_a_seq_does_not_smuggle_through_a_non_transcript_source():
    # Passing seq on a git jewel must not resolve — the CHECK constraint would
    # reject the row anyway, but it should never get that far.
    idx = candidate_index(COMMITS, "git")
    assert resolve_anchor({"seq": 41, "ref": "nope"}, "git", idx) is None


def test_sources_do_not_share_an_allowlist():
    # A ref valid for one source must not validate under another's index.
    docs = candidate_index([{"ref": "NEWSROOM.md#L1-L20", "date": DAY}], "doc")
    assert resolve_anchor({"ref": "abc1234"}, "doc", docs) is None
    assert resolve_anchor({"ref": "NEWSROOM.md#L1-L20"}, "doc", docs) is not None
