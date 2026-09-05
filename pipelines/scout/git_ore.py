"""The git reader — commit history as mineable ore.

The first non-transcript source, and the one that exists to fix a specific
problem: **session logs record a problem while it is being fought.** They are
the richest source of decisions and temporal anchors and they are not rich
narrative candidates, because the resolution that makes a story is not in them
(NEWSROOM.md §The Scout's sources, corrected 2026-09-04). Commit messages carry
the opposite register — what was decided and why, written *after* — and there
are 1,527 of them across the estate averaging 106 words in this repo alone.

Deliberately NOT a reuse of `blog_pipeline/git_reader.py`, though two things are
taken from it: shelling out to a local `git log` rather than the GitHub API (the
repos are on this box; no rate limits, no cost), and its record format, which
separates fields with `\\x1f` and records with `\\x1e`. That second one is the
genuinely clever bit — a commit body contains newlines and every printable
delimiter anyone reaches for first, so ASCII unit/record separators are the only
safe choice.

What differs, and why:

* **The estate, not one repo.** `source_ref` is therefore `repo@sha` and never a
  bare sha — two repos can and will produce shas that mean nothing to each
  other, and `resolve_anchor` has no way to tell them apart without the
  qualifier. Once written, these refs are in every jewel mined from git, so the
  shape is settled here rather than discovered later.
* **No cursor.** ADR-002 argues for one coverage ledger over six bespoke
  cursors, and that ledger is not built. Until it is, this reader takes an
  explicit range and the operator drives it, exactly as `--walk` does.
* **No diff stats, no author email.** The jewel is mined from the *message*.
  Line counts are prompt noise, and an address on a path that reaches a
  published note is a leak with no upside.
* **A bounded candidate page.** `read_commits` returns rows shaped for
  `jewels.candidate_index(rows, "git")` — each carrying `ref` and `date`. That
  is the anti-hallucination contract: schema 1.4.0 traded away the foreign key
  for non-transcript sources on the understanding that `resolve_anchor` checks
  every citation against the set the walker was actually shown.

Author date, not commit date: it is when the work happened, which is what
`scout_jewel.session_date` promises to mean for every source. Commit date drifts
on rebase.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

# Field and record separators — see the module docstring.
FIELD, RECORD = "\x1f", "\x1e"
LOG_FORMAT = f"%h{FIELD}%aI{FIELD}%s{FIELD}%b{RECORD}"

# Long enough to be unambiguous across these repos, short enough to read in a
# note's sources line, which is where a source_ref eventually surfaces.
ABBREV = 10

# Mirrors walk.ROW_CLIP_CHARS: enough to catch a jewel, small enough that a page
# of them stays a cheap call. The full message is one `git show` away.
COMMIT_CLIP_CHARS = 1200

# MEASURED 2026-09-05, and smaller than the transcript page on purpose. Sizing
# this by input length was the wrong axis: 150 commits is comparable to a
# 150-row transcript page in CHARACTERS, and it blew the 4096-token OUTPUT
# ceiling less than halfway through, so the JSON came back truncated and the
# whole page parsed to nothing.
#
# Density of JEWELS, not density of text, is what the page has to be sized
# against. Measured at 50 commits: 13 jewels, 1,005 output tokens, `end_turn`.
# Extrapolated, 150 commits wants roughly 4,000 — which is what blew the
# ceiling. So the ratio is about one jewel per four commits, and 50 leaves
# real headroom rather than sitting on the edge.
#
# (An earlier version of this comment guessed "roughly one jewel per commit"
# on the reasoning that a commit message is a decision-with-reason by
# construction. The reasoning is sound and the number was wrong by 4x; the
# walker is selective about what counts as durable even here. Corrected from
# measurement 2026-09-05 rather than left to look like it had been known.)
DEFAULT_PAGE = 50


def read_commits(
    repos: list[Path],
    since: str | None = None,
    until: str | None = None,
    limit: int = DEFAULT_PAGE,
) -> list[dict]:
    """A bounded, chronological page of commits across several repos.

    Merges are skipped: they carry no authored reasoning, which is the whole
    reason this source is worth mining.
    """
    rows: list[dict] = []
    for repo in repos:
        repo = Path(repo)
        if not (repo / ".git").exists():
            continue
        cmd = [
            "git", "-C", str(repo), "log", "--reverse", "--no-merges",
            f"--abbrev={ABBREV}", f"--pretty=format:{LOG_FORMAT}",
        ]
        if since:
            cmd.append(f"--since={since}")
        if until:
            cmd.append(f"--until={until}")
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        for record in out.split(RECORD):
            record = record.strip("\n")
            if not record:
                continue
            parts = record.split(FIELD)
            if len(parts) < 4:
                continue
            sha, authored, subject, body = parts[:4]
            rows.append({
                "ref": f"{repo.name}@{sha}",
                "date": authored[:10],          # DATE, to match session_date
                "repo": repo.name,
                "subject": subject.strip(),
                "body": body.strip(),
            })
    # One chronological page across the whole estate. Sorting by date and then
    # by ref keeps a page stable between runs when several commits share a day.
    rows.sort(key=lambda r: (r["date"], r["ref"]))
    return rows[:limit]


def page_as_prompt(rows: list[dict]) -> str:
    """The page the walker is shown, and the set it is held to.

    The `[ref=...]` tag mirrors the transcript page's `[seq=...]`, for the same
    reason: the walker cites back what it was shown, and anything else is
    dropped by `resolve_anchor` rather than reaching the table.

    **The date sits OUTSIDE the bracket, and that is not cosmetic.** The first
    live run had it as `[ref=X 2025-10-01]`, and the model copied the whole tag
    body — every jewel came back as `"ref": "repo@sha 2025-10-01"`. The guard
    worked exactly as designed and dropped all of them, which is the failure
    mode this shape exists to prevent: a page that costs full price and
    persists nothing. The bracket now contains the ref and nothing else.
    """
    out = []
    for r in rows:
        text = f"{r['subject']}\n{r['body']}".strip()
        if len(text) > COMMIT_CLIP_CHARS:
            text = text[:COMMIT_CLIP_CHARS] + " …(clipped)"
        out.append(f"[ref={r['ref']}] committed {r['date']}\n{text}")
    return "\n\n".join(out)
