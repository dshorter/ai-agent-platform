"""The Director's eyes — a fresh, compact state snapshot per registered project,
plus the open to-do list already bucketed.

Volatile layer only for now (git: branch, recent commits, working-tree; ops
todos). Durable context (design docs / ADRs) is a later slice. Read fresh each
turn, matching the persona's "rank from what you read just now."
"""
from __future__ import annotations

import importlib.util
import subprocess
from datetime import datetime
from importlib.machinery import SourceFileLoader
from pathlib import Path

from pipelines.director.registry import Project, load_registry

_OPS = Path(__file__).resolve().parents[2] / "ops"
_REPO_DOCS = Path(__file__).resolve().parents[2] / "docs" / "director"
LEDGER_BUDGET = 40_000  # chars of ledger injected per turn before compaction is due


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


def todos_digest() -> str:
    """The open to-do list, bucketed by ops/calendar-views' own projection.

    Injected rather than discovered. The raw calendar is the wrong shape for a
    reading agent — past the read tool's byte ceiling (so a whole-file read drops
    the newest todos) and record-structured against line-oriented grep. On
    2026-08-11 the morning brief spent 8 of 12 tool calls rebuilding this list by
    hand, found the assembled view on call 12, and hit its step cap before it
    could use it. calendar-views already computes these buckets for todos.html;
    this is the same projection as text.
    """
    views = _OPS / "calendar-views"
    try:
        # An extensionless script: no finder locates it by name, but an explicit
        # source loader imports it fine, and main() is __main__-guarded.
        spec = importlib.util.spec_from_loader(
            "calendar_views", SourceFileLoader("calendar_views", str(views))
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.emit_digest(module.parse((_OPS / "calendar.ics").read_text()))
    except Exception as exc:  # a bad calendar degrades the brief, never kills it
        return (f"(ops todos unavailable: {exc} — the to-do list could not be "
                f"projected; say so rather than guessing at what is due)")


def ledger() -> str:
    """The Director's own ledger, injected rather than discovered.

    Read every turn for the same reason the to-do digest is: something needed on
    every turn should not cost a tool call to find. Bounded — if the file outgrows
    the budget the contract calls for compaction, and this surfaces that rather
    than silently clipping (the 2026-08-03 calendar lesson, applied to its own
    memory).
    """
    path = _REPO_DOCS / "director-ledger.md"
    try:
        text = path.read_text()
    except OSError:
        return ""  # no ledger yet is a normal state, not an error
    if len(text) > LEDGER_BUDGET:
        text = text[:LEDGER_BUDGET] + (
            f"\n…(ledger past its {LEDGER_BUDGET:,}-char injection budget — "
            f"{len(text):,} chars total. Older entries are NOT shown. Propose a "
            f"compaction per the read contract.)")
    return text


def gather_state() -> str:
    projects = load_registry()
    if not projects:
        return ""
    blocks = "\n\n".join(snapshot(p) for p in projects)
    # The clock line exists because the model otherwise has NO date source and
    # infers one (2026-07-13: it ran a day fast, declared that morning's Scout
    # leads "not run today" and reframed a tomorrow-VTODO as due-today).
    clock = datetime.now().astimezone().strftime("%A %Y-%m-%d %H:%M %Z")
    parts = [f"CURRENT PROJECT STATE (read just now; clock: {clock}):",
             todos_digest(), blocks]
    memory = ledger()
    if memory:
        # Last, and labelled: it is the one block here that is NOT current state.
        parts.append("YOUR LEDGER — your own notes from past runs. Pattern "
                     "recognition only: check new findings for rhymes against these "
                     "before calling them novel. NEVER cite it for what is true now; "
                     "the blocks above and your tools are for that.\n\n" + memory)
    return "\n\n".join(parts)
