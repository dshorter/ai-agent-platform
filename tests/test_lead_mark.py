"""Tests for lead_mark — the leads ledger's only mutation verb.

Why this file exists: on 2026-08-03 the draft review desk was found to be
emitting `--to spiked` for leads at status `drafted`, which is not a legal
transition. It had never worked, for every card it displayed, and the failure
was invisible because the refusal goes to stderr and the desk is a static
snapshot that shows no state at all. A `rejected` state was added to close it.

So these tests guard the transition TABLE, not the file-writing mechanics: the
table is the contract that a typo or a well-meant "simplification" can silently
break, and nothing downstream would notice until an operator's paste did
nothing again.

Every test runs against a temporary copy of a synthetic ledger. lead_mark
resolves LEDGER at call time specifically so a `path=` override works — its own
docstring records that a default bound at import once caused a verification run
to mark the real file.

    .venv/bin/python -m pytest tests/ -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.scout.lead_mark import TRANSITIONS, mark  # noqa: E402

# The flat-YAML shape leads.py writes. Two leads so a test can prove a mark
# never touches the block next door.
LEDGER = """\
# Scout leads
leads:
  - id: lead-one
    filed: 2026-07-01
    status: {status_one}
    register: note
    pitch: >-
      A first lead, for marking.
    sources:
      - session abc turns 1-2
  - id: lead-two
    filed: 2026-07-02
    status: new
    register: note
    pitch: >-
      A second lead, which must never be touched.
    sources:
      - session def turns 3-4
"""


@pytest.fixture
def ledger(tmp_path):
    """A factory: build a ledger whose first lead sits at a chosen status."""
    def build(status_one="new"):
        p = tmp_path / "leads.yaml"
        p.write_text(LEDGER.format(status_one=status_one), encoding="utf-8")
        return p
    return build


def status_of(path: Path, lead_id: str) -> str:
    """Read one lead's status straight out of the file, not via the module —
    a test that reuses the parser under test can't catch the parser."""
    block = path.read_text(encoding="utf-8").split(f"- id: {lead_id}\n")[1]
    for line in block.splitlines():
        if line.strip().startswith("status:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("- id:"):
            break
    raise AssertionError(f"no status for {lead_id}")


# ── the table itself ─────────────────────────────────────────────────────────

def test_table_is_the_documented_lifecycle():
    """new -> claimed -> drafted -> approved -> published, with two exits."""
    assert TRANSITIONS == {
        "claimed":   ({"new"}, "editor"),
        "spiked":    ({"new", "claimed"}, "editor"),
        "drafted":   ({"claimed"}, "writer"),
        "approved":  ({"drafted"}, "editor"),
        "rejected":  ({"drafted"}, "editor"),
        "published": ({"approved"}, "publisher"),
    }


def test_spiked_and_rejected_are_distinct_verdicts():
    """The bug this file was written for. `spiked` means the lead was never
    worth pursuing; `rejected` means it was, and the draft failed. Only the
    second is a signal about the Writer, so their prior states must not
    overlap — if they ever do, one of them has been quietly collapsed."""
    spiked_from, _ = TRANSITIONS["spiked"]
    rejected_from, _ = TRANSITIONS["rejected"]
    assert spiked_from.isdisjoint(rejected_from)
    assert "drafted" in rejected_from and "drafted" not in spiked_from


def test_every_state_a_draft_can_reach_is_reachable_from_drafted():
    """Regression guard for the original defect: a lead at `drafted` must have
    at least one exit the review desk can offer, in BOTH directions."""
    exits = {to for to, (frm, _) in TRANSITIONS.items() if "drafted" in frm}
    assert exits == {"approved", "rejected"}


# ── legal transitions ────────────────────────────────────────────────────────

@pytest.mark.parametrize("frm,to,by", [
    ("new", "claimed", "editor"),
    ("new", "spiked", "editor"),
    ("claimed", "spiked", "editor"),
    ("claimed", "drafted", "writer"),
    ("drafted", "approved", "editor"),
    ("drafted", "rejected", "editor"),
    ("approved", "published", "publisher"),
])
def test_legal_transition_applies(ledger, frm, to, by):
    p = ledger(frm)
    mark("lead-one", to=to, by=by, path=p)
    assert status_of(p, "lead-one") == to


def test_stamp_accumulates_and_keeps_the_timeline(ledger):
    """Stamps are the point: a rejected lead still carries when it was claimed
    and drafted, which is what makes Writer-quality trends readable off the
    file."""
    p = ledger("claimed")
    mark("lead-one", to="drafted", by="writer", on="2026-07-30", path=p)
    mark("lead-one", to="rejected", by="editor", on="2026-08-03", path=p)
    text = p.read_text(encoding="utf-8")
    assert "drafted_on: 2026-07-30 (writer)" in text
    assert "rejected_on: 2026-08-03 (editor)" in text
    assert text.index("drafted_on") < text.index("rejected_on")


def test_mark_never_touches_the_neighbouring_lead(ledger):
    p = ledger("drafted")
    before = p.read_text(encoding="utf-8").split("- id: lead-two\n")[1]
    mark("lead-one", to="rejected", by="editor", path=p)
    assert p.read_text(encoding="utf-8").split("- id: lead-two\n")[1] == before


# ── refusals ─────────────────────────────────────────────────────────────────

def test_the_original_bug_still_refuses(ledger):
    """drafted -> spiked: what the review desk emitted for months. It must stay
    refused — `rejected` was added as the right answer, not as a loosening of
    `spiked`."""
    p = ledger("drafted")
    with pytest.raises(SystemExit) as e:
        mark("lead-one", to="spiked", by="editor", path=p)
    assert "not a legal transition" in str(e.value)
    assert status_of(p, "lead-one") == "drafted"


@pytest.mark.parametrize("frm,to", [
    ("rejected", "approved"),   # terminal: no resurrection
    ("rejected", "published"),
    ("spiked", "claimed"),
    ("new", "rejected"),        # cannot skip drafted
    ("new", "published"),
    ("published", "approved"),  # never un-published
])
def test_illegal_transition_refuses_and_writes_nothing(ledger, frm, to):
    p = ledger(frm)
    original = p.read_text(encoding="utf-8")
    with pytest.raises(SystemExit):
        mark("lead-one", to=to, by="editor", path=p)
    assert p.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("to,wrong_actor", [
    ("rejected", "writer"),     # the editor rejects, not the writer
    ("approved", "writer"),
    ("drafted", "editor"),      # the writer stamps drafted
    ("published", "editor"),
])
def test_wrong_actor_refuses(ledger, to, wrong_actor):
    frm = next(iter(TRANSITIONS[to][0]))
    p = ledger(frm)
    with pytest.raises(SystemExit) as e:
        mark("lead-one", to=to, by=wrong_actor, path=p)
    assert "stamped by" in str(e.value)


def test_unknown_state_refuses(ledger):
    p = ledger("drafted")
    with pytest.raises(SystemExit) as e:
        mark("lead-one", to="binned", by="editor", path=p)
    assert "unknown state" in str(e.value)


def test_unknown_lead_refuses(ledger):
    p = ledger("new")
    with pytest.raises(SystemExit):
        mark("lead-nine", to="claimed", by="editor", path=p)


# ── the review desk's respect for a verdict ──────────────────────────────────
#
# Regression guard for a real failure on 2026-08-03: four leads were marked
# `rejected` and the desk still listed all six drafts as awaiting review. The
# desk filtered on "is this slug already in notes.json" and nothing else, and it
# read the status embedded in the draft FILE — a snapshot frozen at draft time
# that says `claimed` forever. A verdict the desk itself collected had no effect
# on the desk.

import importlib.util  # noqa: E402

_TOOLS = Path(__file__).resolve().parent.parent / "tools"
sys.path.insert(0, str(_TOOLS))
_spec = importlib.util.spec_from_file_location("draft_review", _TOOLS / "draft_review.py")
_dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dr)


def _draft(slug, status):
    return {"note": {"slug": slug}, "lead": {"id": f"lead-{slug}", "status": status}}


@pytest.mark.parametrize("status,shown", [
    ("drafted", True),      # the only status still needing a verdict
    ("rejected", False),    # the bug: these used to stay on the desk
    ("approved", False),
    ("published", False),
    ("spiked", False),
])
def test_desk_shows_only_undecided_drafts(status, shown):
    assert _dr.is_pending(_draft("s", status), set()) is shown


def test_desk_hides_anything_already_promoted():
    assert _dr.is_pending(_draft("s", "drafted"), {"s"}) is False


def test_desk_shows_a_draft_whose_lead_is_missing():
    """Fail open, not closed: an unmatched draft is surfaced rather than
    silently dropped, because a vanished card is unnoticeable."""
    assert _dr.is_pending({"note": {"slug": "s"}, "lead": {}}, set()) is True
    assert _dr.is_pending({"note": {"slug": "s"}}, set()) is True


def test_live_status_overrides_the_frozen_snapshot(tmp_path):
    """The ledger wins. This is the whole fix."""
    ledger = tmp_path / "leads.yaml"
    ledger.write_text(
        "leads:\n"
        "  - id: lead-a\n    status: rejected\n    register: note\n"
        "  - id: lead-b\n    status: drafted\n    register: note\n",
        encoding="utf-8")
    drafts = [
        {"note": {"slug": "a"}, "lead": {"id": "lead-a", "status": "claimed"}},
        {"note": {"slug": "b"}, "lead": {"id": "lead-b", "status": "claimed"}},
    ]
    changed = _dr.apply_live_status(drafts, ledger)
    assert changed == 2
    assert drafts[0]["lead"]["status"] == "rejected"
    assert drafts[1]["lead"]["status"] == "drafted"
    assert _dr.is_pending(drafts[0], set()) is False
    assert _dr.is_pending(drafts[1], set()) is True


def test_missing_ledger_is_not_fatal(tmp_path):
    drafts = [{"note": {"slug": "a"}, "lead": {"id": "lead-a", "status": "drafted"}}]
    assert _dr.apply_live_status(drafts, tmp_path / "nope.yaml") == 0
    assert drafts[0]["lead"]["status"] == "drafted"


# ── who wore the hat: agent-applied marks and the concordance metric ─────────
# On 2026-08-03 the gate-① concordance read 6/6 — but all six claims had been
# stamped `--by editor` by an AGENT session on 07-30, almost certainly working
# from the Wire Editor's own proposals. A machine agreeing with a machine.
# The fix is provenance: `--agent` stamps `(<role>, agent)`, and concordance
# counts only human dispositions. These tests keep both halves honest.

import re  # noqa: E402

from pipelines.wire_editor.config import WireEditorConfig  # noqa: E402
from pipelines.wire_editor.run import concordance  # noqa: E402


def test_agent_flag_lands_in_the_stamp(ledger):
    p = ledger()
    mark("lead-one", to="claimed", by="editor", path=p, agent=True)
    assert "    claimed_on: " in p.read_text()
    assert re.search(r"^    claimed_on: \d{4}-\d{2}-\d{2} \(editor, agent\)$",
                     p.read_text(), re.M)


def test_human_stamp_is_unchanged_by_default(ledger):
    p = ledger()
    mark("lead-one", to="claimed", by="editor", path=p)
    assert re.search(r"^    claimed_on: \d{4}-\d{2}-\d{2} \(editor\)$",
                     p.read_text(), re.M)


PROPOSALS = """\
proposals:
  - id: lead-human
    wire: claim
    chief: claim
    chief_verdict: claim
  - id: lead-robot
    wire: claim
    chief: claim
    chief_verdict: claim
"""


def _concordance_config(tmp_path) -> WireEditorConfig:
    state = tmp_path / "state"
    (state / "proposals").mkdir(parents=True)
    (state / "proposals" / "2026-07-18.yaml").write_text(PROPOSALS, encoding="utf-8")
    return WireEditorConfig(
        postgres_dsn="", anthropic_api_key="", wire_model="", chief_model="",
        leads_path=tmp_path / "leads.yaml", state_dir=state,
    )


def _concordance_ledger(tmp_path, robot_stamp: str) -> None:
    (tmp_path / "leads.yaml").write_text(
        "leads:\n"
        "  - id: lead-human\n    status: claimed\n"
        "    claimed_on: 2026-07-30 (editor)\n"
        "  - id: lead-robot\n    status: claimed\n"
        f"    claimed_on: {robot_stamp}\n",
        encoding="utf-8")


def test_concordance_counts_only_human_dispositions(tmp_path):
    cfg = _concordance_config(tmp_path)
    _concordance_ledger(tmp_path, "2026-07-30 (editor, agent)")
    report = concordance(cfg)
    assert "1 disposed — wire 1/1, chief 1/1 (1 agent-applied, excluded)" in report
    assert "TOTAL wire: 1/1" in report


def test_concordance_with_only_agent_marks_is_unscored(tmp_path):
    """The poisoned shape itself: every disposition agent-applied. The report
    must refuse to produce a percentage rather than print a flattering one."""
    cfg = _concordance_config(tmp_path)
    (tmp_path / "leads.yaml").write_text(
        "leads:\n"
        "  - id: lead-human\n    status: claimed\n"
        "    claimed_on: 2026-07-30 (editor, agent)\n"
        "  - id: lead-robot\n    status: claimed\n"
        "    claimed_on: 2026-07-30 (editor, agent)\n",
        encoding="utf-8")
    report = concordance(cfg)
    assert "%" not in report
    assert "no human dispositions yet" in report
    assert "2 agent-applied marks excluded" in report


def test_concordance_spike_reads_the_spike_stamp(tmp_path):
    """A lead claimed by an agent but SPIKED by the human is a human routing
    verdict — the disposing stamp is spiked_on, not claimed_on."""
    cfg = _concordance_config(tmp_path)
    (tmp_path / "leads.yaml").write_text(
        "leads:\n"
        "  - id: lead-human\n    status: spiked\n"
        "    claimed_on: 2026-07-30 (editor, agent)\n"
        "    spiked_on: 2026-08-03 (editor)\n"
        "  - id: lead-robot\n    status: claimed\n"
        "    claimed_on: 2026-07-30 (editor, agent)\n",
        encoding="utf-8")
    report = concordance(cfg)
    # human spiked it, wire said claim: a real, scored disagreement
    assert "1 disposed — wire 0/1, chief 0/1 (1 agent-applied, excluded)" in report
