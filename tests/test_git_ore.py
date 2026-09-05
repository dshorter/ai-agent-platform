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
        assert f"[ref={r['ref']} {r['date']}]" in prompt
        assert "the body explains why." in prompt


def test_no_author_email_reaches_the_page(tmp_path):
    """A source_ref and its page reach a published note. An address on that
    path is a leak with no upside."""
    rows = read_commits([_repo(tmp_path, "alpha", ["a"])])
    assert "FIXTURE-AUTHOR-IDENTITY" not in page_as_prompt(rows)
    assert not any("FIXTURE-AUTHOR" in str(v) for r in rows for v in r.values())
