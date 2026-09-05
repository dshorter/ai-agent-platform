"""The dedup payload digest — leads.load_pitched(pitch_chars=...).

The payload is the dominant term in the synthesis prompt's cost and grows with
the ledger forever. These tests pin the two properties that matter: the digest
keeps what dedup matches on, and it does not widen what the Scout is shown.
"""
from pathlib import Path

from pipelines.scout.leads import _digest, load_pitched

LEDGER = """\
leads:
  - id: 2026-07-12-a-real-slug
    filed: 2026-07-12
    status: spiked
    register: blog
    pitch: >-
      A cost anomaly hunt flipped its own framing: the label was wrong and the run was not
      anomalous. It was full-price re-sends of accumulated context. Marking the transcript
      dropped billed tokens by 76%, deployed the same day.
    why_now: >-
      The fix is live and the pricing window makes it timely.
    redaction: required
  - id: 2026-07-13-second-lead
    filed: 2026-07-13
    status: new
    pitch: >-
      Short pitch that fits.
    redaction: required
"""


def _write(tmp_path: Path) -> Path:
    p = tmp_path / "leads.yaml"
    p.write_text(LEDGER, encoding="utf-8")
    return p


def test_none_is_the_pre_2026_09_behaviour(tmp_path):
    """The full-text arm of the verification must still be reachable."""
    full = load_pitched(_write(tmp_path))
    assert full[0]["pitch"].startswith("A cost anomaly hunt")
    assert full[0]["pitch"].endswith("deployed the same day.")


def test_digest_cuts_on_a_sentence_and_keeps_the_claim(tmp_path):
    """At a limit that bites, the cut lands on a sentence end, not mid-word."""
    got = load_pitched(_write(tmp_path), 120)
    # The story's claim — what dedup matches on — survives, whole.
    assert got[0]["pitch"] == (
        "A cost anomaly hunt flipped its own framing: the label was wrong "
        "and the run was not anomalous."
    )
    # It really is shorter than the full text, or the knob does nothing.
    assert len(got[0]["pitch"]) < len(load_pitched(_write(tmp_path))[0]["pitch"])


def test_a_pitch_under_the_limit_is_returned_whole(tmp_path):
    """The fixture's first pitch is 222 chars; at 240 nothing should change."""
    full = load_pitched(_write(tmp_path))[0]["pitch"]
    assert load_pitched(_write(tmp_path), 240)[0]["pitch"] == full


def test_ids_are_never_truncated(tmp_path):
    """The id is a semantic slug and carries half the dedup signal."""
    for lead in load_pitched(_write(tmp_path), 40):
        assert lead["id"] in ("2026-07-12-a-real-slug", "2026-07-13-second-lead")


def test_short_pitches_are_untouched_and_unmarked(tmp_path):
    got = load_pitched(_write(tmp_path), 240)
    assert got[1]["pitch"] == "Short pitch that fits."
    assert "…" not in got[1]["pitch"]


def test_pineapple_no_status_reaches_the_scout_at_any_limit(tmp_path):
    """The digest shortens what is read; it must never widen it.

    The ledger fixture carries `status: spiked` — an Editor verdict. If it ever
    appears in what load_pitched returns, the dedup payload has become the
    backpropagation channel the newsroom is built not to have.
    """
    for limit in (None, 40, 240, 10_000):
        for lead in load_pitched(_write(tmp_path), limit):
            assert set(lead) == {"id", "pitch"}
            assert "spiked" not in lead["pitch"]
            assert "status" not in lead["pitch"]


def test_digest_falls_back_to_a_word_boundary_with_a_marker():
    """No sentence end in range — cut on a word and say so."""
    long_clause = "a mid-sentence pitch that runs on and on without any full stop at all here"
    got = _digest(long_clause, 30)
    assert got.endswith(" …")
    assert not got.startswith(" ")
    assert len(got) <= 32
    assert " ".join(got.split()) == got  # no ragged whitespace from the cut


def test_digest_does_not_cut_at_a_sentence_that_is_uselessly_early():
    """A full stop in the first third would leave a digest with no claim in it."""
    pitch = "Yes. " + "then the actual substance of the pitch continues for a long while here"
    got = _digest(pitch, 60)
    assert got != "Yes."
    assert "substance" in got
