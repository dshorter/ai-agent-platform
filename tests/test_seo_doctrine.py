"""Tests for the SEO doctrine loader and the doctrine files it serves.

Two kinds of test here, and the second kind is the point.

The INTRINSIC tests always run: the loader behaves, and the shipped doctrine
does not contain the specific claims that were wrong before. Those are the
regressions — a wrong hostname and a stale indexing claim lived in a hardcoded
prompt for roughly three months because nothing could see them.

The DRIFT test runs only on the box, where the human source of truth
(/opt/_host/SEO.md) exists. That doc is local-only and deliberately outside this
public repo, so the test skips cleanly for anyone who clones.

    .venv/bin/python -m pytest tests/test_seo_doctrine.py -q
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agents.seo_doctrine import DOCTRINE_DIR, load_doctrine

SOURCE_OF_TRUTH = Path("/opt/_host/SEO.md")

SINKS = sorted(p.stem for p in DOCTRINE_DIR.glob("*.md"))


# ── the loader ───────────────────────────────────────────────────────────────

def test_at_least_one_sink_ships():
    assert SINKS, f"no doctrine files found in {DOCTRINE_DIR}"


def test_blog_sink_loads():
    assert load_doctrine("blog").strip()


def test_missing_sink_raises_rather_than_returning_empty():
    with pytest.raises(FileNotFoundError, match="no SEO doctrine for sink"):
        load_doctrine("no-such-sink")


def test_empty_doctrine_raises(tmp_path):
    (tmp_path / "hollow.md").write_text("   \n", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match="is empty"):
        load_doctrine("hollow", doctrine_dir=tmp_path)


# ── the regressions: claims that were wrong before ───────────────────────────

@pytest.mark.parametrize("sink", SINKS)
def test_no_phantom_blog_path_on_the_apex(sink):
    """The blog is a subdomain. There is no /blog path on the apex, and the old
    hardcoded prompt claimed there was."""
    text = load_doctrine(sink).lower()
    assert "uzelhub.com/blog" not in text


@pytest.mark.parametrize("sink", SINKS)
def test_no_indexing_posture_in_a_public_repo(sink):
    """Doctrine files carry operational rules only. Indexing strategy lives in
    the local source of truth — this repo is public, and a push is a publish."""
    text = load_doctrine(sink).lower()
    for leaked in ("noindex", "quarantin", "scaled content"):
        assert leaked not in text, f"{sink}.md leaks strategy: {leaked!r}"


def test_blog_names_the_real_host():
    assert "blog.uzelhub.com" in load_doctrine("blog")


def test_composed_prompt_carries_role_and_doctrine():
    from agents.marketer_agent import MARKETER_ROLE_PROMPT, build_system_prompt

    composed = build_system_prompt("blog")
    assert MARKETER_ROLE_PROMPT in composed
    assert load_doctrine("blog") in composed


# ── the drift test ───────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not SOURCE_OF_TRUTH.is_file(),
    reason=f"{SOURCE_OF_TRUTH} not present — local-only source of truth",
)
@pytest.mark.parametrize(
    "claim,in_doctrine,in_playbook",
    [
        ("blog hostname", "blog.uzelhub.com", "blog.uzelhub.com"),
        ("apex hostname", "uzelhub.com", "uzelhub.com"),
        ("title length", "50-60", "57"),
    ],
)
def test_doctrine_and_playbook_agree(claim, in_doctrine, in_playbook):
    """Cheap agreement check on the facts both documents state.

    Not a semantic diff — it cannot be. It catches the failure that actually
    happened: one document being edited and the other silently left behind."""
    doctrine = load_doctrine("blog")
    playbook = SOURCE_OF_TRUTH.read_text(encoding="utf-8")
    assert in_doctrine in doctrine, f"{claim}: missing from config/seo/blog.md"
    assert in_playbook in playbook, f"{claim}: missing from {SOURCE_OF_TRUTH}"


@pytest.mark.skipif(
    not SOURCE_OF_TRUTH.is_file(),
    reason=f"{SOURCE_OF_TRUTH} not present — local-only source of truth",
)
def test_playbook_names_where_the_extract_lives():
    """The pointer has to survive in the other direction too, or the next person
    edits the playbook and never learns the agent reads a different file."""
    playbook = SOURCE_OF_TRUTH.read_text(encoding="utf-8")
    assert "config/seo/" in playbook
