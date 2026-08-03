"""Tests for wire_review — the routing desk (gate ①'s surface).

The desk exists because step 3 had never been exercised: the shortlist was
unreachable and applying verdicts meant hand-typing. These tests guard the
two things that would silently rot: the artifact parser (hand-rolled flat
YAML, written by _artifact() in pipelines/wire_editor/run.py) and the
pending/disposed split (the draft desk's stale-status bug, same class).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
_spec = importlib.util.spec_from_file_location("wire_review", _TOOLS / "wire_review.py")
_wr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wr)


ARTIFACT = """\
# Wire Editor proposals — 2026-08-03 12:00 (wire: m1, chief shadow: m2)
# Apply verdicts (the operator's pen, the artifact never self-applies):
#   .venv/bin/python -m pipelines.scout.lead_mark <id> --to claimed|spiked --by editor
# Concordance report: python -m pipelines.wire_editor --concordance
date: 2026-08-03
clusters:
  - theme: "A theme, with commas"
    ids: [lead-a, lead-b]
proposals:
  - id: lead-a
    wire: claim
    register: note
    reason: "Worth pursuing, it says"
    chief: agree
    chief_verdict: claim
    chief_reason: "Concur"
  - id: lead-b
    wire: spike
    register: blog
    reason: "Fold elsewhere"
    flags: [employer-gate]
    chief: differ
    chief_verdict: claim
    chief_reason: "Actually distinct"
  - id: lead-c
    wire: hold
    register: note
    reason: "Too soon"
    chief: silent
"""


def _art(tmp_path):
    p = tmp_path / "2026-08-03.yaml"
    p.write_text(ARTIFACT, encoding="utf-8")
    return _wr.parse_artifact(p)


def test_parser_reads_the_artifact_dialect(tmp_path):
    art = _art(tmp_path)
    assert art["date"] == "2026-08-03"
    assert art["clusters"] == [{"theme": "A theme, with commas", "ids": ["lead-a", "lead-b"]}]
    a, b, c = art["proposals"]
    assert (a["id"], a["wire"], a["chief"], a["chief_verdict"]) == ("lead-a", "claim", "agree", "claim")
    assert a["reason"] == "Worth pursuing, it says"
    assert b["flags"] == ["employer-gate"]
    assert (b["chief"], b["chief_verdict"]) == ("differ", "claim")
    assert c["wire"] == "hold" and c["chief"] == "silent" and "chief_verdict" not in c


def test_only_new_leads_await_routing(tmp_path):
    """The draft desk's bug class: a disposed lead must not be re-asked."""
    art = _art(tmp_path)
    leads = {
        "lead-a": {"id": "lead-a", "status": "new"},
        "lead-b": {"id": "lead-b", "status": "claimed"},
        "lead-c": {"id": "lead-c", "status": "spiked"},
    }
    pending, decided = _wr.split_by_status(art["proposals"], leads)
    assert [p["id"] for p in pending] == ["lead-a"]
    assert decided == 2


def test_missing_lead_is_shown_not_hidden(tmp_path):
    """Fail open: a proposal the ledger has never heard of is surfaced and
    flagged, because a card that silently vanishes is unnoticeable."""
    art = _art(tmp_path)
    pending, decided = _wr.split_by_status(art["proposals"], {})
    assert [p["id"] for p in pending] == ["lead-a", "lead-b", "lead-c"]
    assert all(p.get("_missing") for p in pending)
    assert decided == 0


def test_page_orders_claims_first_and_never_emits_agent(tmp_path):
    art = _art(tmp_path)
    leads = {p["id"]: {"id": p["id"], "status": "new", "pitch": "A pitch."}
             for p in art["proposals"]}
    page, stats = _wr.build(art, leads)
    assert stats == {"pending": 3, "decided": 0, "claim": 1, "hold": 1, "spike": 1, "differ": 1}
    # attention order: the claim card renders before the hold before the spike
    order = [page.index(f'data-lead="lead-{x}"') for x in ("a", "c", "b")]
    assert order == sorted(order)
    # the human's pen: the desk must never paste an agent-attributed verdict
    assert "--agent" not in page
    assert "--by editor" in page


def test_merge_later_artifact_wins(tmp_path):
    """Backlogs page across artifacts (the 64k ceiling forced --limit), so
    the desk merges — and a re-proposed lead carries the latest verdict."""
    (tmp_path / "a").mkdir()
    p1 = tmp_path / "a" / "2026-08-01.yaml"
    p2 = tmp_path / "a" / "2026-08-03.yaml"
    p1.write_text(ARTIFACT, encoding="utf-8")
    p2.write_text(
        "date: 2026-08-03\nclusters:\nproposals:\n"
        "  - id: lead-c\n    wire: claim\n    register: note\n"
        '    reason: "Ripened"\n    chief: agree\n'
        "    chief_verdict: claim\n    chief_reason: \"Now yes\"\n",
        encoding="utf-8")
    art = _wr.merge_artifacts([p1, p2])
    assert len(art["proposals"]) == 3
    by_id = {p["id"]: p for p in art["proposals"]}
    assert by_id["lead-c"]["wire"] == "claim"          # later file won
    assert by_id["lead-a"]["wire"] == "claim"          # untouched survives
    assert art["date"] == "2026-08-03"
