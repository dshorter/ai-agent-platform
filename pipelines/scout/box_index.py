"""A map of the box's files, so the roam has coordinates instead of guesses.

A jewel's anchor points the roam at a transcript row or a commit. Nothing ever
told it what FILES exist. Measured 2026-09-06: of 104 roam tool calls, 96
followed a jewel's anchor and 8 were exploratory `read_file`/`grep` calls that
guessed a path. All 8 failed. From inside the loop a refusal and a missing file
look alike, so a guess that misses teaches nothing and the model stops looking.

This builds a bounded index of the readable text files under the registered
roots — path, size, mtime, first heading — and rides in the synthesis context
beside the map tail.

It is navigation, never taste. It says what exists and where, and nothing about
what is worth writing about; no disposition, no ranking by interest, nothing
downstream of an Editor verdict ever reaches it (the pineapple rule).

What it leaves out, and why:

  * generated and gitignored trees (`state/`, `.git`, `node_modules`, `.venv`,
    caches): `state/` in particular holds the transcript-derived ledgers, which
    are not the roam's business and are not in the tracked tree.
  * anything without a text suffix, and anything over `MAX_FILE_BYTES`: there is
    no heading to read and no reason to name it.
  * files the toolbox would refuse to open anyway (`looks_secret`). Listing a
    path the roam cannot read recreates the exact dead end this removes.
  * any entry whose own emitted line trips the redaction gate.

That last exclusion is deliberately scoped to the LINE, not the file's body.
What this module publishes is a path and a heading, and both travel into the
model's context and can reach a lead's `citations`, which are publishable text
— so the line is the thing that has to be clean. It does not scan file bodies:
a file whose contents are sensitive is still a file the roam may legitimately
open, and `ToolBox` guards that end. Widening this to bodies would drop
`sysadmin-ledger.md` and half of `docs/` for material the Scout is meant to
read.
"""
from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from pipelines.director.registry import load_registry
from pipelines.director.tools import looks_secret

# The cap the plan set. It is a context budget, not a taste judgment: past a few
# hundred lines the index costs more attention than the guessing it replaces.
INDEX_MAX_LINES = 300
MAX_FILE_BYTES = 2_000_000
_HEADING_CHARS = 78
_HEAD_BYTES = 4096  # enough to reach a heading past a frontmatter block

_SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".cache", "dist", "build", "htmlcov",
    "site-packages", ".idea", ".vscode", "state",
}
_TEXT_SUFFIXES = {
    ".md", ".py", ".sql", ".json", ".yaml", ".yml", ".txt", ".html", ".js",
    ".mjs", ".css", ".sh", ".toml", ".cfg", ".ini", ".csv", ".ics",
}
# Prose first when the cap binds: a doc says what a thing is for, and that is
# what an exploratory read is usually reaching for. `.md` only — the box's
# `.txt` files are overwhelmingly generated dumps (metrics snapshots, log
# spills), which is the opposite of a self-description.
_DOC_SUFFIXES = {".md"}
# Docs outnumber the cap on their own, so the split is what keeps code visible
# at all. Either side takes the other's slack when it underfills.
_DOC_SHARE = 0.65
_COMMENT_MARKERS = ("#", "//", "--", "/*", "*", ";")


def _heading(path: Path) -> str:
    """The file's first self-description, or "". Reads only the first bytes."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(_HEAD_BYTES)
    except OSError:
        return ""
    lines = head.splitlines()
    suffix = path.suffix.lower()

    if suffix == ".md":
        start = 0
        if lines and lines[0].strip() == "---":  # frontmatter
            for i, line in enumerate(lines[1:], start=1):
                if line.strip() == "---":
                    start = i + 1
                    break
        for line in lines[start:]:
            if line.lstrip().startswith("#"):
                return line.lstrip().lstrip("#").strip()[:_HEADING_CHARS]
        return ""

    if suffix == ".py":
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            for quote in ('"""', "'''"):
                if not stripped.startswith(quote):
                    continue
                rest = stripped[len(quote):].strip().rstrip(quote).strip()
                if rest:
                    return rest[:_HEADING_CHARS]
                # `"""` alone on the opening line — the summary is the next one.
                for nxt in lines[i + 1:]:
                    if nxt.strip():
                        return nxt.strip().rstrip(quote).strip()[:_HEADING_CHARS]
                return ""
            break
        return ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for marker in _COMMENT_MARKERS:
            if stripped.startswith(marker):
                return stripped[len(marker):].strip("*/ ").strip()[:_HEADING_CHARS]
        return ""
    return ""


def _size(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1000:
        return f"{n // 1000}k"
    return f"{n}b"


def _candidates(roots: list[Path]) -> list[tuple[Path, os.stat_result]]:
    out: list[tuple[Path, os.stat_result]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(
                d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")
            )
            for name in sorted(filenames):
                p = Path(dirpath) / name
                if p.suffix.lower() not in _TEXT_SUFFIXES or looks_secret(p):
                    continue
                if p.is_symlink():
                    continue  # CLAUDE.md -> AGENTS.md: one file, one line
                try:
                    st = p.stat()
                except OSError:
                    continue
                if st.st_size > MAX_FILE_BYTES:
                    continue
                out.append((p, st))
    return out


def _ranked(candidates: list[tuple[Path, os.stat_result]], cap: int) -> list[tuple[Path, os.stat_result]]:
    """Docs shallowest-first, then everything else most-recently-touched first.

    Three judgments, all navigational. Docs and code answer different
    questions — a doc is looked up by where it lives, a code file is
    interesting when it moved lately. Shallow beats deep among docs because
    depth is where generated piles live: `AGENTS.md` and `docs/uzelhub-crew/`
    are design, `data/metrics_snapshot_*/` is exhaust. And the cap is split
    rather than filled in order, because docs alone overflow it — first-past-
    the-post left zero code files in the index and buried the real docs under
    snapshot dumps.
    """
    docs = sorted(
        (c for c in candidates if c[0].suffix.lower() in _DOC_SUFFIXES),
        key=lambda c: (len(c[0].parts), str(c[0])),
    )
    rest = sorted(
        (c for c in candidates if c[0].suffix.lower() not in _DOC_SUFFIXES),
        key=lambda c: -c[1].st_mtime,
    )
    doc_cap = int(cap * _DOC_SHARE)
    take_docs = docs[:doc_cap]
    take_rest = rest[: cap - len(take_docs)]
    # Whichever side underfilled hands its slack back to the other.
    take_docs = docs[: cap - len(take_rest)]
    return take_docs + take_rest


def build(roots: list[Path] | None = None, cap: int = INDEX_MAX_LINES) -> str:
    """The index as the model sees it. Never raises: a broken index is a
    degraded roam, not a failed synthesis."""
    try:
        paths = roots if roots is not None else [Path(p.path) for p in load_registry()]
        rows = _ranked(_candidates([Path(p) for p in paths]), cap)
    except Exception:  # pragma: no cover - the roam survives without coordinates
        return ""
    if not rows:
        return ""

    from pipelines.writer.redaction import scan  # local: keeps import cost off the walk

    lines: list[str] = []
    for path, st in rows:
        stamp = datetime.fromtimestamp(st.st_mtime).strftime("%m-%d")
        heading = _heading(path)
        line = f"{path}  {_size(st.st_size)}  {stamp}"
        if heading:
            line += f"  {heading}"
        if list(scan(line)):
            continue
        lines.append(line)

    if not lines:
        return ""
    return (
        f"Readable files under the registered roots ({len(lines)} of "
        f"{len(rows)} indexed, {date.today().isoformat()}). These paths exist "
        "and read_file/grep will open them; a path not listed here may still "
        "exist, but guess at your own cost.\n" + "\n".join(lines)
    )
