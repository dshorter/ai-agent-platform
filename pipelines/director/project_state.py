"""The Director's eyes — a fresh, compact state snapshot per registered project,
plus the open to-do list already bucketed.

Volatile layer only for now (git: branch, recent commits, working-tree; ops
todos). Durable context (design docs / ADRs) is a later slice. Read fresh each
turn, matching the persona's "rank from what you read just now."
"""
from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from importlib.machinery import SourceFileLoader
from pathlib import Path

from pipelines.director.registry import Project, load_registry

_OPS = Path(__file__).resolve().parents[2] / "ops"
_REPO_DOCS = Path(__file__).resolve().parents[2] / "docs" / "director"
LEDGER_BUDGET = 40_000  # chars of ledger injected per turn before compaction is due

# The predictor is the largest paid-API spender on the box -- more than the rest
# of the crew combined -- and its databases are the only place its cost lives.
_PREDICTOR_DB_DIR = Path(
    os.environ.get("DIRECTOR_PREDICTOR_DB_DIR", "/opt/predictor_ingest/data/db")
)


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


def predictor_spend(days: int = 7) -> str:
    """What the predictor has actually cost, per domain, injected every turn.

    Injected rather than discovered, for the same reason the to-do digest is:
    the numbers live in per-domain SQLite files under another repo, and a
    reading agent asked "what are we spending" would burn its step budget
    rediscovering that every morning.

    Dollars here are what was CHARGED, not list price. Extraction runs through
    the Batch API at half rate, and `billing_mode` (predictor, 2026-08-31) is
    what makes that distinction; before it, every extraction dollar was recorded
    at roughly 2x. Unpriced calls are surfaced rather than dropped -- a total
    that silently omits them is how five weeks of Sonnet 5 spend went unnoticed.

    Opened read-only: the Director reports on the predictor, it never writes to
    it, and the URI mode makes that a property of the connection rather than a
    promise in a docstring.
    """
    if not _PREDICTOR_DB_DIR.is_dir():
        return ""
    today = datetime.now().date()
    since = (today - timedelta(days=days - 1)).isoformat()
    month_start = today.replace(day=1).isoformat()

    lines, total_window, total_month, unpriced = [], 0.0, 0.0, 0
    for db in sorted(_PREDICTOR_DB_DIR.glob("*.db")):
        try:
            conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        except sqlite3.Error:
            continue
        try:
            window = conn.execute(
                """SELECT COALESCE(SUM(cost_usd), 0),
                          SUM(CASE WHEN cost_usd IS NULL THEN 1 ELSE 0 END)
                     FROM token_usage WHERE run_date >= ?""",
                (since,),
            ).fetchone()
            month = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM token_usage WHERE run_date >= ?",
                (month_start,),
            ).fetchone()
            last = conn.execute(
                """SELECT run_date, COALESCE(SUM(cost_usd), 0)
                     FROM token_usage GROUP BY run_date ORDER BY run_date DESC LIMIT 1"""
            ).fetchone()
        except sqlite3.Error:
            continue  # a domain without the table is simply not reporting yet
        finally:
            conn.close()
        w, u, m = float(window[0]), int(window[1] or 0), float(month[0])
        if not (w or m):
            continue
        total_window += w
        total_month += m
        unpriced += u
        tail = f", last billed {last[0]} ${float(last[1]):.2f}" if last else ""
        lines.append(f"  {db.stem}: ${w:.2f} in {days}d, ${m:.2f} MTD{tail}")

    if not lines:
        return ""
    ceiling = os.environ.get("PREDICTOR_MAX_COST_USD", "15")
    head = (f"PREDICTOR SPEND (actual dollars charged, batch-aware; "
            f"per-run_date ceiling ${ceiling}):")
    foot = f"  TOTAL: ${total_window:.2f} in {days}d, ${total_month:.2f} month-to-date"
    if unpriced:
        foot += (f"\n  ⚠ {unpriced} call(s) in the window have NO price on file — "
                 f"the totals above are incomplete, say so if you cite them")
    return "\n".join([head, *lines, foot])


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
    spend = predictor_spend()
    if spend:
        parts.append(spend)
    memory = ledger()
    if memory:
        # Last, and labelled: it is the one block here that is NOT current state.
        parts.append("YOUR LEDGER — your own notes from past runs. Pattern "
                     "recognition only: check new findings for rhymes against these "
                     "before calling them novel. NEVER cite it for what is true now; "
                     "the blocks above and your tools are for that.\n\n" + memory)
    return "\n\n".join(parts)
