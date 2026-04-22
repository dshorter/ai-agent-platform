"""
Reads commit history from a local git repository by shelling out to `git log`.

Deliberately does not use the GitHub API — predictor_ingest sits on the same
VPS as this pipeline, so a local read avoids rate limits and API costs.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


GIT_LOG_FORMAT = "%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1f%b%x1e"
SHA_LINE_SEP = "\x1e"
FIELD_SEP = "\x1f"


@dataclass
class Commit:
    sha: str
    author_name: str
    author_email: str
    author_date: datetime
    subject: str
    body: str
    files_changed: list[str]
    additions: int
    deletions: int

    def to_dict(self) -> dict:
        return {
            "sha": self.sha,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "author_date": self.author_date.isoformat(),
            "subject": self.subject,
            "body": self.body,
            "files_changed": self.files_changed,
            "additions": self.additions,
            "deletions": self.deletions,
        }


class GitReader:
    """Reads commits from a local git working copy."""

    def __init__(self, repo_path: str | Path) -> None:
        self.repo_path = Path(repo_path).resolve()
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repo: {self.repo_path}")

    def log(
        self,
        since_sha: str | None = None,
        max_count: int | None = None,
    ) -> list[Commit]:
        """Return commits in chronological order (oldest first).

        If since_sha is provided, returns commits *after* that SHA.
        """
        revision_range = f"{since_sha}..HEAD" if since_sha else "HEAD"
        cmd = [
            "git",
            "-C",
            str(self.repo_path),
            "log",
            "--reverse",
            f"--pretty=format:{GIT_LOG_FORMAT}",
            revision_range,
        ]
        if max_count is not None:
            cmd.insert(4, f"--max-count={max_count}")

        raw = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        ).stdout

        commits = []
        for record in raw.split(SHA_LINE_SEP):
            record = record.strip("\n")
            if not record:
                continue
            parts = record.split(FIELD_SEP)
            if len(parts) < 6:
                continue
            sha, author_name, author_email, author_date, subject, body = parts[:6]
            files, adds, dels = self._shortstat(sha)
            commits.append(
                Commit(
                    sha=sha,
                    author_name=author_name,
                    author_email=author_email,
                    author_date=datetime.fromisoformat(author_date),
                    subject=subject,
                    body=body.strip(),
                    files_changed=files,
                    additions=adds,
                    deletions=dels,
                )
            )
        return commits

    def _shortstat(self, sha: str) -> tuple[list[str], int, int]:
        """Per-commit file list and line counts. Two git calls, fine for our volume."""
        files_cmd = [
            "git",
            "-C",
            str(self.repo_path),
            "show",
            "--pretty=format:",
            "--name-only",
            sha,
        ]
        files = [
            line.strip()
            for line in subprocess.run(
                files_cmd, capture_output=True, text=True, check=True
            ).stdout.splitlines()
            if line.strip()
        ]

        numstat_cmd = [
            "git",
            "-C",
            str(self.repo_path),
            "show",
            "--pretty=format:",
            "--numstat",
            sha,
        ]
        adds = dels = 0
        for line in subprocess.run(
            numstat_cmd, capture_output=True, text=True, check=True
        ).stdout.splitlines():
            if not line.strip():
                continue
            cols = line.split("\t")
            if len(cols) >= 2 and cols[0].isdigit() and cols[1].isdigit():
                adds += int(cols[0])
                dels += int(cols[1])
        return files, adds, dels

    def head_sha(self) -> str:
        return subprocess.run(
            ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
