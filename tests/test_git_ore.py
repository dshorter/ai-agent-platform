"""The git reader, and the contract that replaced the foreign key.

Schema 1.4.0 dropped `NOT NULL` on `seq` so five other sources could produce a
jewel, and gave up the DB-level anti-hallucination guarantee for them in the
process. `jewels.resolve_anchor` is what it was traded for. These tests exercise
the git reader against that contract, because a git sha has no table to
reference and nothing else stands between an invented citation and a row.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.scout.git_ore import page_as_prompt, read_commits  # noqa: E402
from pipelines.scout.jewels import candidate_index, resolve_anchor  # noqa: E402


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout


def _repo(tmp_path: Path, name: str, subjects: list[str]) -> Path:
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    # A non-address identity on purpose: the redaction gate blocked an
    # email-shaped fixture here, and the right answer was to change the
    # fixture rather than dismiss the finding into a public repo's
    # allow.txt forever. The assertion below is unchanged in strength --
    # it checks that the author identity, whatever it is, never reaches
    # the page the walker sees.
    _git(repo, "config", "user.email", "FIXTURE-AUTHOR-IDENTITY")
    _git(repo, "config", "user.name", "T")
    for i, subj in enumerate(subjects):
        (repo / f"f{i}.txt").write_text(str(i))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", f"{subj}\n\nthe body explains why.")
    return repo


def test_ref_is_repo_qualified_never_a_bare_sha(tmp_path):
    """Two repos can produce shas that mean nothing to each other, and
    resolve_anchor cannot tell them apart without the qualifier."""
    a = _repo(tmp_path, "alpha", ["first thing"])
    rows = read_commits([a])
    assert len(rows) == 1
    ref = rows[0]["ref"]
    assert ref.startswith("alpha@")
    assert len(ref.split("@")[1]) == 10


def test_the_row_shape_is_what_candidate_index_expects(tmp_path):
    """This is the join to the anti-hallucination control — if the reader stops
    emitting `ref` and `date`, the guard silently indexes nothing."""
    rows = read_commits([_repo(tmp_path, "alpha", ["a", "b"])])
    index = candidate_index(rows, "git")
    assert set(index) == {r["ref"] for r in rows}
    assert all(len(d) == 10 and d[4] == "-" for d in index.values())  # YYYY-MM-DD


def test_a_ref_that_was_shown_resolves(tmp_path):
    rows = read_commits([_repo(tmp_path, "alpha", ["a"])])
    index = candidate_index(rows, "git")
    got = resolve_anchor({"ref": rows[0]["ref"], "note": "n"}, "git", index)
    assert got == (rows[0]["ref"], rows[0]["date"])


def test_an_invented_sha_is_refused(tmp_path):
    rows = read_commits([_repo(tmp_path, "alpha", ["a"])])
    index = candidate_index(rows, "git")
    assert resolve_anchor({"ref": "alpha@deadbeef00"}, "git", index) is None


def test_a_bare_sha_is_refused(tmp_path):
    """Dropping the repo qualifier must not resolve — it is the thing that
    makes the anchor unique across the estate."""
    rows = read_commits([_repo(tmp_path, "alpha", ["a"])])
    index = candidate_index(rows, "git")
    bare = rows[0]["ref"].split("@")[1]
    assert resolve_anchor({"ref": bare}, "git", index) is None


def test_a_prefix_of_a_real_ref_is_refused(tmp_path):
    """Exact match only — no fuzzy sha resolution, which would let a truncated
    hallucination land on a real commit."""
    rows = read_commits([_repo(tmp_path, "alpha", ["a"])])
    index = candidate_index(rows, "git")
    assert resolve_anchor({"ref": rows[0]["ref"][:-2]}, "git", index) is None


def test_one_repos_ref_does_not_resolve_against_anothers_page(tmp_path):
    a = _repo(tmp_path, "alpha", ["a"])
    b = _repo(tmp_path, "beta", ["b"])
    only_b = candidate_index(read_commits([b]), "git")
    a_ref = read_commits([a])[0]["ref"]
    assert resolve_anchor({"ref": a_ref}, "git", only_b) is None


def test_merges_are_skipped(tmp_path):
    """A merge carries no authored reasoning, which is the only reason this
    source is worth mining."""
    repo = _repo(tmp_path, "alpha", ["base"])
    _git(repo, "checkout", "-q", "-b", "side")
    (repo / "side.txt").write_text("x")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "side work")
    _git(repo, "checkout", "-q", "main")
    (repo / "main.txt").write_text("y")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "main work")
    _git(repo, "merge", "-q", "--no-ff", "-m", "Merge branch 'side'", "side")
    subjects = [r["subject"] for r in read_commits([repo])]
    assert "Merge branch 'side'" not in subjects
    assert {"base", "side work", "main work"} == set(subjects)


def test_the_page_is_bounded_and_chronological(tmp_path):
    rows = read_commits([_repo(tmp_path, "alpha", [f"c{i}" for i in range(6)])], limit=3)
    assert len(rows) == 3
    assert [r["date"] for r in rows] == sorted(r["date"] for r in rows)


def test_a_missing_repo_is_skipped_not_fatal(tmp_path):
    """One unreadable repo must not take the whole estate's walk down."""
    a = _repo(tmp_path, "alpha", ["a"])
    rows = read_commits([a, tmp_path / "not-a-repo"])
    assert len(rows) == 1


def test_the_prompt_tags_every_commit_with_its_ref(tmp_path):
    """The walker cites back what it was shown; the tag is how it knows."""
    rows = read_commits([_repo(tmp_path, "alpha", ["a", "b"])])
    prompt = page_as_prompt(rows)
    for r in rows:
        assert f"[ref={r['ref']}] committed {r['date']}" in prompt
        assert "the body explains why." in prompt


def test_no_author_email_reaches_the_page(tmp_path):
    """A source_ref and its page reach a published note. An address on that
    path is a leak with no upside."""
    rows = read_commits([_repo(tmp_path, "alpha", ["a"])])
    assert "FIXTURE-AUTHOR-IDENTITY" not in page_as_prompt(rows)
    assert not any("FIXTURE-AUTHOR" in str(v) for r in rows for v in r.values())


# --- the three defects the first live run exposed ------------------------------

def test_the_date_is_outside_the_ref_bracket(tmp_path):
    """The first live run had `[ref=X DATE]` and the model copied the whole tag
    body, so every jewel came back as `repo@sha 2025-10-01` and every one was
    dropped. The guard did its job; the page still cost full price and
    persisted nothing. The bracket holds the ref and nothing else."""
    rows = read_commits([_repo(tmp_path, "alpha", ["a"])])
    line = page_as_prompt(rows).splitlines()[0]
    assert line.startswith(f"[ref={rows[0]['ref']}]")
    assert rows[0]["date"] not in line.split("]")[0]


def test_a_ref_with_the_date_appended_is_refused(tmp_path):
    """Belt and braces: even if a model appends it, the guard must not accept."""
    rows = read_commits([_repo(tmp_path, "alpha", ["a"])])
    index = candidate_index(rows, "git")
    from pipelines.scout.jewels import resolve_anchor as ra
    assert ra({"ref": f"{rows[0]['ref']} {rows[0]['date']}"}, "git", index) is None


def test_the_git_page_is_sized_by_jewel_yield_not_text_length():
    """150 commits blew the 4096-token output ceiling less than halfway
    through. A commit is a decision-with-reason by construction, so the walker
    emits roughly one jewel per commit — density of jewels is the axis."""
    from pipelines.scout.git_ore import DEFAULT_PAGE
    assert DEFAULT_PAGE <= 60


def test_truncation_raises_instead_of_looking_like_an_empty_page():
    """The defect: _parse_json returns {} for incomplete JSON, so a page that
    blew the ceiling was indistinguishable from a page with nothing in it."""
    from agents.scout_agent import ScoutCall, TriageTruncated, _guard_truncation
    truncated = ScoutCall(data={}, model="m", stop_reason="max_tokens",
                          raw_text='{"jewels": [{"ref": "a@b"')
    with pytest.raises(TriageTruncated):
        _guard_truncation(truncated, "git")


def test_a_clean_empty_page_is_not_an_error():
    """A page really can hold nothing mineable. Only truncation is the fault."""
    from agents.scout_agent import ScoutCall, _guard_truncation
    _guard_truncation(ScoutCall(data={"jewels": []}, model="m",
                                stop_reason="end_turn"), "git")


def test_a_full_but_parseable_page_is_not_an_error():
    """stop_reason max_tokens with usable data is a different situation and
    must not abort a walk that produced real jewels."""
    from agents.scout_agent import ScoutCall, _guard_truncation
    _guard_truncation(ScoutCall(data={"jewels": [{"ref": "a@b"}]}, model="m",
                                stop_reason="max_tokens"), "git")


def test_synthesis_truncation_raises_like_triage():
    """The expensive stage had the hole the cheap one got fixed for.

    A synthesis call hit exactly 20,000 output tokens, made no tool calls,
    returned unparseable JSON and reported `leads: 0` for $0.43 — which reads
    identically to "the model had nothing to pitch".
    """
    from agents.scout_agent import ScoutCall, TriageTruncated, _guard_truncation
    with pytest.raises(TriageTruncated):
        _guard_truncation(
            ScoutCall(data={}, model="m", stop_reason="max_tokens",
                      raw_text='{"leads": [{"slug": "half-a-'), "synthesis")


def test_empty_result_keeps_the_model_words(tmp_path, monkeypatch):
    """Three zero-lead runs cost $2.72 and none could be diagnosed, because the
    only record was `leads: 0` and the raw response died with the process."""
    import agents.scout_agent as m
    from agents.scout_agent import ScoutCall, _keep_evidence_if_empty
    monkeypatch.setattr(m, "__file__", str(tmp_path / "agents" / "scout_agent.py"))
    (tmp_path / "agents").mkdir()
    call = ScoutCall(data={}, model="claude-sonnet-5", stop_reason="end_turn",
                     raw_text="I looked and found nothing worth pitching.")
    _keep_evidence_if_empty(call, "synthesis")
    written = list((tmp_path / "pipelines" / "scout" / "state" / "empty-calls").glob("*.txt"))
    assert len(written) == 1
    body = written[0].read_text()
    assert "nothing worth pitching" in body and "end_turn" in body


def test_a_result_with_leads_writes_no_residue(tmp_path, monkeypatch):
    """Only failures leave debugging residue — this is not provenance."""
    import agents.scout_agent as m
    from agents.scout_agent import ScoutCall, _keep_evidence_if_empty
    monkeypatch.setattr(m, "__file__", str(tmp_path / "agents" / "scout_agent.py"))
    (tmp_path / "agents").mkdir()
    _keep_evidence_if_empty(
        ScoutCall(data={"leads": [{"slug": "x"}]}, model="m", raw_text="..."), "synthesis")
    assert not (tmp_path / "pipelines").exists()


def test_guard_reports_the_ceiling_that_actually_applies():
    """The first version hardcoded the triage ceiling into both messages, so a
    synthesis failure reported 4,096 when the real limit was 20,000 — an
    instrument misreporting the number it exists to report."""
    from agents.scout_agent import ScoutCall, TriageTruncated, _guard_truncation
    with pytest.raises(TriageTruncated, match="20,000"):
        _guard_truncation(ScoutCall(data={}, model="m", stop_reason="max_tokens",
                                    raw_text='{"leads": [{'), "synthesis")
    with pytest.raises(TriageTruncated, match="4,096"):
        _guard_truncation(ScoutCall(data={}, model="m", stop_reason="max_tokens",
                                    raw_text='{"jewels": [{'), "git")


def test_no_text_at_all_is_a_different_diagnosis_than_truncated_json():
    """0 chars means nothing was written to truncate, so 'the page is too big'
    is wrong advice. The budget went somewhere other than the answer."""
    from agents.scout_agent import ScoutCall, TriageTruncated, _guard_truncation
    with pytest.raises(TriageTruncated, match="NO TEXT AT ALL"):
        _guard_truncation(ScoutCall(data={}, model="m", stop_reason="max_tokens",
                                    raw_text=""), "synthesis")
