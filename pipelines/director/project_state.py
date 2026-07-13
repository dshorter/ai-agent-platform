"""The Director's eyes — a fresh, compact state snapshot per registered project.

Volatile layer only for now (git: branch, recent commits, working-tree). Durable
context (design docs / ADRs) is a later slice. Read fresh each turn, matching the
persona's "rank from what you read just now."
"""
from __future__ import annotations

import subprocess
from datetime import datetime

from pipelines.director.registry import Project, load_registry


def _git(path: str, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", path, *args],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (out.stdout or out.stderr).strip()
    except Exception as exc:  # missing repo, git error, etc. — report, don't crash
        return f"(git error: {exc})"


def snapshot(project: Project) -> str:
    branch = _git(project.path, "rev-parse", "--abbrev-ref", "HEAD")
    log = _git(project.path, "log", "--oneline", "-n", "8")
    status_lines = _git(project.path, "status", "--short").splitlines()
    if not status_lines:
        working = "clean"
    else:
        shown = "\n".join(status_lines[:8])
        more = "\n  …" if len(status_lines) > 8 else ""
        working = f"{len(status_lines)} uncommitted change(s):\n{shown}{more}"

    parts = [f"## {project.name}  (path: {project.path}, branch: {branch})"]
    if project.note:
        parts.append(project.note)
    parts.append("Recent commits:\n" + (log or "(none)"))
    parts.append("Working tree: " + working)
    return "\n".join(parts)


def gather_state() -> str:
    projects = load_registry()
    if not projects:
        return ""
    blocks = "\n\n".join(snapshot(p) for p in projects)
    # The clock line exists because the model otherwise has NO date source and
    # infers one (2026-07-13: it ran a day fast, declared that morning's Scout
    # leads "not run today" and reframed a tomorrow-VTODO as due-today).
    clock = datetime.now().astimezone().strftime("%A %Y-%m-%d %H:%M %Z")
    return f"CURRENT PROJECT STATE (read just now; clock: {clock}):\n\n" + blocks
