"""
Filters trivial commits and groups the rest into story batches.

The batching heuristic is intentionally simple for Sprint Zero — consecutive
commits within a time window that touch overlapping file sets cluster
together. Tune on real output before reaching for Haiku here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import timedelta

from pipelines.blog_pipeline.git_reader import Commit


TRIVIAL_SUBJECT_PATTERNS = [
    re.compile(r"^(chore|style|format|typo|bump|ci|build|deps)\b", re.IGNORECASE),
    re.compile(r"^merge\b", re.IGNORECASE),
    re.compile(r"^revert\b", re.IGNORECASE),
    re.compile(r"^wip\b", re.IGNORECASE),
]

TRIVIAL_MAX_LINES = 5
DEFAULT_WINDOW = timedelta(hours=48)


@dataclass
class CommitBatch:
    commits: list[Commit] = field(default_factory=list)

    @property
    def start_sha(self) -> str:
        return self.commits[0].sha if self.commits else ""

    @property
    def end_sha(self) -> str:
        return self.commits[-1].sha if self.commits else ""

    @property
    def total_lines(self) -> int:
        return sum(c.additions + c.deletions for c in self.commits)

    @property
    def file_set(self) -> set[str]:
        return {f for c in self.commits for f in c.files_changed}


def is_trivial(commit: Commit) -> bool:
    """Regex + line-count heuristic. Cheap, no LLM call."""
    for pattern in TRIVIAL_SUBJECT_PATTERNS:
        if pattern.match(commit.subject):
            return True
    if (commit.additions + commit.deletions) <= TRIVIAL_MAX_LINES:
        return True
    return False


def filter_trivial(commits: list[Commit]) -> list[Commit]:
    return [c for c in commits if not is_trivial(c)]


def group_into_batches(
    commits: list[Commit],
    window: timedelta = DEFAULT_WINDOW,
) -> list[CommitBatch]:
    """Group consecutive commits by time-window proximity and file overlap.

    A new batch starts when the time gap exceeds the window OR the file set
    has no overlap with the current batch's file set.
    """
    if not commits:
        return []

    batches: list[CommitBatch] = []
    current = CommitBatch(commits=[commits[0]])

    for commit in commits[1:]:
        gap = commit.author_date - current.commits[-1].author_date
        overlaps = bool(set(commit.files_changed) & current.file_set)
        if gap > window or not overlaps:
            batches.append(current)
            current = CommitBatch(commits=[commit])
        else:
            current.commits.append(commit)

    batches.append(current)
    return batches
