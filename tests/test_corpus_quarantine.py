"""Tests for the quarantine classifier — the part that decides what gets written.

Pure function, no network: `classify` is where a mistake would be expensive
(270 posts), and it is the only place in the tool that makes a judgement.

    .venv/bin/python -m pytest tests/test_corpus_quarantine.py -q
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "corpus_quarantine", _REPO / "tools" / "corpus_quarantine.py")
cq = importlib.util.module_from_spec(_spec)
sys.modules["corpus_quarantine"] = cq
_spec.loader.exec_module(cq)

STAMPED = {"slug": "a-corpus-post", "codeinjection_head": cq.ROBOTS_META}
BARE = {"slug": "a-corpus-post", "codeinjection_head": None}


def test_bare_corpus_post_gets_stamped():
    assert cq.classify(BARE, lift=False) == "change"


def test_stamped_post_is_left_alone():
    assert cq.classify(STAMPED, lift=False) == "already"


def test_stamp_is_idempotent_around_whitespace():
    padded = {"slug": "a", "codeinjection_head": f"\n  {cq.ROBOTS_META}  \n"}
    assert cq.classify(padded, lift=False) == "already"


def test_lift_reverses_the_verdicts():
    assert cq.classify(STAMPED, lift=True) == "change"
    assert cq.classify(BARE, lift=True) == "already"


def test_indexed_tier_is_never_touched():
    # Quarantining the chapters would empty the index by construction.
    for slug in cq.NOT_CORPUS_SLUGS:
        assert cq.classify({"slug": slug, "codeinjection_head": None},
                           lift=False) == "skip-not-corpus"


def test_foreign_injection_is_skipped_not_clobbered():
    foreign = {"slug": "a", "codeinjection_head": "<script>hi</script>"}
    assert cq.classify(foreign, lift=False) == "skip-foreign-injection"
    assert cq.classify(foreign, lift=True) == "skip-foreign-injection"


def test_the_meta_tag_carries_follow():
    # `follow` is the whole reason publishing the corpus beats sitting on it:
    # equity keeps flowing to the chapters while it is quarantined.
    assert "noindex" in cq.ROBOTS_META and "follow" in cq.ROBOTS_META


def test_payload_never_carries_status_or_newsletter():
    # A quarantine batch must not be able to publish or to mail anything.
    post = {"id": "abc", "updated_at": "2026-09-01T00:00:00.000Z", "slug": "a"}
    fields = cq.payload_for(post, lift=False)["posts"][0]
    assert set(fields) == {"id", "updated_at", "codeinjection_head"}


def test_lift_payload_nulls_the_field_rather_than_emptying_it():
    # Ghost clears the injection on null; "" would leave an empty tag behind.
    post = {"id": "abc", "updated_at": "2026-09-01T00:00:00.000Z", "slug": "a"}
    assert cq.payload_for(post, lift=True)["posts"][0]["codeinjection_head"] is None


def test_payload_carries_updated_at_for_collision_safety():
    post = {"id": "abc", "updated_at": "2026-09-01T00:00:00.000Z", "slug": "a"}
    assert cq.payload_for(post, lift=False)["posts"][0]["updated_at"] == post["updated_at"]
