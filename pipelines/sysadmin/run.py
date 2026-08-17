"""One reconciliation pass: gather state, run the loop, persist the artifacts.

Stateless shape, same as the rest of the crew: load state, read fresh, reason,
persist, exit. The pass produces up to three artifacts —

  1. the report, written whole to the proposals directory (the primary output;
     design §Operating loop: nothing is applied without operator approval),
  2. a decisions row on the spine (agent_name='sysadmin' — deliberate; the
     spine stores the tool_sequence name, per the Wire Editor's observation),
  3. optionally one ledger entry, appended via the constrained ops/ledger-append
     helper (write exception 4) and git-committed with attribution.

If Postgres is down the pass still runs — a dead spine is exactly the kind of
thing this agent may be diagnosing — and the decision trace lands in
state/decisions-fallback.jsonl instead (the design's fallback mitigation).
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import os
import re
import subprocess
from pathlib import Path

from anthropic import Anthropic

from agents.sysadmin_agent import SysadminAgent, SysadminReply
from pipelines.blog_pipeline.pricing import compute_cost
from pipelines.sysadmin.config import REPO_ROOT, SysadminConfig
from pipelines.sysadmin.tools import MAX_READ_BYTES


log = logging.getLogger("uzelhub_crew.sysadmin")

FALLBACK_LOG = REPO_ROOT / "pipelines" / "sysadmin" / "state" / "decisions-fallback.jsonl"
LEDGER_HELPER = REPO_ROOT / "ops" / "ledger-append"
# Shared operator pager. The runner (not the agent) sends: the agent stays
# read-only + proposals/ledger, external comm is the pipeline's job — the bot is
# a pager, not a channel the model can drive (design §Notifications).
NOTIFY_HELPER = "/usr/local/sbin/notify-telegram"

DAILY_CHARTER = """Daily reconciliation pass. Audit coverage and drift, reading fresh. Work these checks in order; stop cleanly when budget forces it and report what you did not reach:

1. Schedule coverage: `systemctl list-timers --all`, then reconcile — every executable under /opt/*/scripts and /opt/_host/scripts is either scheduled, invoked by a scheduled unit, or marked manual-only. Unit files that exist as sources but are not installed are loaded guns unloaded; flag them.
2. Unit hygiene: agent/service units in /etc/systemd/system have User=, a Restart= policy or a timer, and OnFailure=notify-telegram@%n.service. Flag gaps.
3. Compose vs reality: `docker ps` labels (com.docker.compose.project) against the compose files in /opt/*/; the server-maintenance overlap rule; any bare compose verbs in scripts.
4. Git posture per /opt/_host/WORKFLOW.md: predictor_prod must be clean; uzelhub-web's working tree should not sit dirty for days; prod trees on main.
5. Root droppings: root-owned files inside the claude-owned repos (bounded `find <repo> -user root` — skip .git internals only if noise drowns signal).
6. Spot-check /opt/_host/README.md claims that your findings above touch (full reconcile is the weekly pass, not today).

Check every finding for rhymes against your ledger and the four case studies before calling it novel. Then write the report per the contract."""

PASSES: dict[str, str] = {
    "daily": DAILY_CHARTER,
}


def _gather_context(config: SysadminConfig, spine_up: bool) -> str:
    """The injected state: clock, identity, ledger prefix. All labelled, all fresh."""
    # The clock line exists because a model without a date source infers one
    # and drifts (the Director ran a day fast, 2026-07-13). Staleness math is
    # this agent's whole job — the real clock is non-negotiable.
    clock = _dt.datetime.now().astimezone().strftime("%A %Y-%m-%d %H:%M %Z")
    try:
        import getpass
        import grp

        user = getpass.getuser()
        groups = ",".join(sorted(g.gr_name for g in grp.getgrall() if user in g.gr_mem))
    except Exception:
        user, groups = "(unknown)", "(unknown)"

    try:
        with config.ledger_path.open("rb") as fh:
            ledger = fh.read(MAX_READ_BYTES).decode("utf-8", errors="ignore")
    except Exception as exc:
        ledger = f"(ledger unreadable: {exc} — that is itself worth a finding)"

    spine_note = "" if spine_up else (
        "\nNOTE: the agent_decisions spine (Postgres) is UNREACHABLE right now — "
        "this run's trace goes to the local fallback log. Treat the dead spine "
        "as finding material; hvac-postgres may be down."
    )
    return (
        f"Clock: {clock}\n"
        f"Running as: {user} (supplementary groups: {groups})\n"
        f"{spine_note}\n\n"
        f"YOUR LEDGER (bounded prefix, newest first — rhyme-check against this):\n\n"
        f"{ledger}"
    )


_LEDGER_SECTION = re.compile(
    r"^## Ledger entry\s*\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
)
_STATUS_LINE = re.compile(r"^## Status:\s*(\S+)", re.MULTILINE)
_PROPOSAL_RE = re.compile(r"^### P\d+\b", re.MULTILINE)
_FINDINGS_SECTION = re.compile(r"^## Findings\s*(.*?)(?=^## |\Z)", re.DOTALL | re.MULTILINE)
_PROPOSALS_SECTION = re.compile(r"^## Proposals\s*(.*?)(?=^## |\Z)", re.DOTALL | re.MULTILINE)

# The helper hard-truncates at 4000 chars (Telegram's own ceiling is 4096), and
# a silently cut proposal is worse than none — you would apply half a diff. So
# the push is all-or-nothing against a budget that leaves room for the
# "[SYSADMIN] " prefix and a header line.
#
# Why proposals and not the whole report: measured across 2026-08-13..16 the
# proposals section ran 2,514-2,995 chars while the full artifact ran 9.1-11.5k.
# Proposals are the part you act on, and they are the part that fits.
PROPOSALS_BUDGET = 3800


def parse_ledger_entry(report: str) -> tuple[str, str] | None:
    """(title, body) from the report's optional '## Ledger entry' section."""
    m = _LEDGER_SECTION.search(report)
    if not m:
        return None
    section = m.group(1).strip()
    tm = re.match(r"TITLE:\s*(.+)", section)
    if not tm:
        return None
    title = tm.group(1).strip()
    body = section[tm.end():].strip()
    if not title or not body:
        return None
    return title, body


def append_ledger(config: SysadminConfig, title: str, body: str) -> str:
    """Write exception 4, exercised by the runner: shell to the constrained
    helper (--author sysadmin hardcoded — the model never holds the pen), then
    git-commit the ledger with attribution, calendar_add-style. Failures warn
    and never fail the pass — the report artifact already carries the entry."""
    if not LEDGER_HELPER.exists():
        return "ledger-append helper missing — entry NOT appended (it is in the report artifact)"
    try:
        proc = subprocess.run(
            [str(LEDGER_HELPER), "--author", "sysadmin", "--title", title,
             "--ledger", str(config.ledger_path)],
            input=body, capture_output=True, text=True, timeout=15,
        )
    except Exception as exc:
        return f"ledger-append failed to run: {exc}"
    out = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        return f"ledger-append refused: {out}"
    commit = subprocess.run(
        ["git", "-C", str(REPO_ROOT),
         "-c", "user.name=Sysadmin Agent", "-c", "user.email=sysadmin@ai-agent-platform",
         "commit", "-o", str(config.ledger_path),
         "-m", f"ledger: {title[:60]} (sysadmin, via ledger-append)"],
        capture_output=True, text=True, timeout=15,
    )
    if commit.returncode != 0:
        return f"{out} (note: appended but git commit failed: {commit.stderr.strip()[:200]})"
    return out


def _log_to_spine(config: SysadminConfig, conn, pass_name: str, charter: str,
                  reply: SysadminReply, artifact: Path | None, status_word: str) -> None:
    from pipelines.blog_pipeline.logging_context import (
        DecisionWriter,
        SequenceAwareLogManager,
    )
    from pipelines.director.store import complete_run, create_run

    run_id = create_run(conn, "sysadmin")
    run_status = "success"
    try:
        log_manager = SequenceAwareLogManager(db_writer=DecisionWriter(conn))
        with log_manager.task_sequence(
            task_id=str(run_id), description=f"sysadmin: {pass_name} pass"
        ):
            with log_manager.tool_sequence("sysadmin", reason=charter[:300]) as ctx:
                ctx.llm_model = reply.model
                ctx.llm_provider = "anthropic"
                ctx.token_count_input = reply.input_tokens
                ctx.token_count_output = reply.output_tokens
                ctx.token_count_cache_create = reply.cache_creation_input_tokens
                ctx.token_count_cache_read = reply.cache_read_input_tokens
                ctx.cost_usd = compute_cost(
                    reply.model, reply.input_tokens, reply.output_tokens,
                    reply.cache_creation_input_tokens, reply.cache_read_input_tokens,
                ) or 0.0
                ctx.payload = {
                    "pass": pass_name,
                    "status": status_word,
                    "artifact": str(artifact) if artifact else None,
                    "report": reply.text[:8000],  # full text lives in the artifact
                    "iterations": reply.iterations,
                    "tool_calls": reply.tool_calls,
                }
    except Exception:
        run_status = "error"
        raise
    finally:
        complete_run(conn, run_id, run_status)


def _log_to_fallback(pass_name: str, reply: SysadminReply, artifact: Path | None,
                     status_word: str, why: str) -> None:
    FALLBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "pass": pass_name,
        "status": status_word,
        "artifact": str(artifact) if artifact else None,
        "model": reply.model,
        "input_tokens": reply.input_tokens,
        "output_tokens": reply.output_tokens,
        "iterations": reply.iterations,
        "spine_error": why[:300],
    }
    with FALLBACK_LOG.open("a") as fh:
        fh.write(json.dumps(row) + "\n")


def _notify(message: str) -> None:
    """Push one line to the operator's Telegram via the shared helper. Delivery
    is the helper's problem (it exits 0 on failure); a launch problem here is
    logged and never fatal — the report artifact and ledger already persisted."""
    try:
        subprocess.run([NOTIFY_HELPER, "SYSADMIN", message], check=False, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("notify-telegram invocation failed: %s", exc)


def _pass_summary(reply_text: str, status_word: str,
                  entry: tuple[str, str] | None, ledger_note: str) -> str:
    """One-line operator digest of a pass outcome for the Telegram push. Stands
    in for the not-yet-built weekly digest: the daily pass is the only loop, so
    silence must mean the run failed (OnFailure), never 'found something'."""
    if status_word == "CLEAN":
        return "daily pass — clean, no new findings."
    if status_word != "FINDINGS":
        return f"daily pass — status {status_word}; check the run output."
    n_prop = len(_PROPOSAL_RE.findall(reply_text))
    fm = _FINDINGS_SECTION.search(reply_text)
    n_find = len(re.findall(r"^\s*-\s+\S", fm.group(1), re.MULTILINE)) if fm else 0
    headline = entry[0] if entry else (f"{n_find} finding(s)" if n_find else "findings logged")
    extras = []
    if n_prop:
        extras.append(f"{n_prop} proposal(s)")
    if entry and all(w not in ledger_note for w in ("NOT appended", "refused", "failed", "missing")):
        extras.append("ledger updated")
    suffix = f" ({', '.join(extras)})" if extras else ""
    return f"daily pass — FINDINGS: {headline}{suffix}. See proposals dir."


def _proposals_push(reply_text: str, artifact: Path | None) -> str | None:
    """The day's proposals, verbatim, when they fit in one page message.

    Returns None when there is nothing worth paging. Never truncates: over
    budget, it says so and points at the artifact rather than sending a diff
    that stops mid-hunk.
    """
    m = _PROPOSALS_SECTION.search(reply_text)
    if not m:
        return None
    body = m.group(1).strip()
    if not body or body.lower().startswith("none this pass"):
        return None
    where = f" — {artifact}" if artifact else ""
    if len(body) > PROPOSALS_BUDGET:
        return (f"proposals for today are {len(body):,} chars, over the "
                f"{PROPOSALS_BUDGET:,} page budget — not truncating{where}")
    return f"today's proposals{where}\n\n{body}"


def run_pass(config: SysadminConfig, pass_name: str, *, dry_run: bool = False) -> None:
    if config.paused:
        # Exit 0 keeps OnFailure quiet — pausing is an operator choice, not a failure.
        print("sysadmin: paused (SYSADMIN_PAUSED set in .env) — remove the line to resume")
        return
    try:
        charter = PASSES[pass_name]
    except KeyError:
        raise SystemExit(f"unknown pass {pass_name!r} — known: {', '.join(sorted(PASSES))}")

    import psycopg

    conn = None
    spine_error = ""
    try:
        conn = psycopg.connect(config.postgres_dsn)
    except Exception as exc:
        spine_error = str(exc)
        log.warning("spine unreachable — falling back to local trace: %s", exc)

    try:
        agent = SysadminAgent(
            Anthropic(api_key=config.anthropic_api_key),
            model=config.model,
            max_cost_usd=config.max_cost_usd,
        )
        log.info("sysadmin.pass.start name=%s model=%s", pass_name, config.model)
        context = _gather_context(config, spine_up=conn is not None)
        reply = agent.run(charter, context=context)

        status_m = _STATUS_LINE.search(reply.text)
        status_word = status_m.group(1) if status_m else "UNPARSED"

        artifact: Path | None = None
        if not dry_run:
            stamp = _dt.date.today().isoformat()
            config.proposals_dir.mkdir(parents=True, exist_ok=True)
            artifact = config.proposals_dir / f"{stamp}-{pass_name}.md"
            n = 2
            while artifact.exists():  # a re-run the same day never clobbers
                artifact = config.proposals_dir / f"{stamp}-{pass_name}-{n}.md"
                n += 1
            artifact.write_text(reply.text + "\n")

        if conn is not None:
            try:
                _log_to_spine(config, conn, pass_name, charter, reply, artifact, status_word)
            except Exception as exc:
                _log_to_fallback(pass_name, reply, artifact, status_word, f"spine write failed: {exc}")
        else:
            _log_to_fallback(pass_name, reply, artifact, status_word, spine_error)
    except BaseException as exc:
        # A failed pass writes no artifact and no ledger entry, so the day it
        # cost becomes invisible — and the next pass's rhyme-check reads the
        # ledger, so a silent gap is a gap it cannot find. That is how the same
        # failure class took three days (07-29, 08-04, 08-08) before anyone saw
        # it was one class: each failure erased its own evidence from the only
        # place the agent looks.
        #
        # Leave a marker, then get out of the way. Three rules, in order:
        #   1. NEVER swallow — the non-zero exit is what fires OnFailure=. The
        #      bare `raise` is load-bearing; the pager is not the gap and must
        #      not become one.
        #   2. NEVER let the marker's own failure mask the original. A broken
        #      failure-handler that eats the real traceback is strictly worse
        #      than no handler.
        #   3. Terse. One dated line naming the error CLASS, which is what a
        #      rhyme-check matches on — three different literal errors were one
        #      shape.
        # BaseException, not Exception: a timeout or SIGTERM mid-pass costs the
        # same day and should leave the same mark.
        if not dry_run:
            try:
                append_ledger(
                    config,
                    f"{pass_name} pass FAILED ({type(exc).__name__}) — no audit performed",
                    f"`sysadmin-daily.service` exited non-zero before producing a report, so "
                    f"no proposals artifact exists for this date and no audit of live state "
                    f"was made.\n\n"
                    f"- Error class: `{type(exc).__name__}`\n"
                    f"- Detail: `journalctl -u sysadmin-daily.service --since {_dt.date.today()}`\n\n"
                    f"Rhyme-check this against other `pass FAILED` entries before treating it "
                    f"as a one-off — this failure class has recurred with different literal "
                    f"errors each time.",
                )
            except BaseException:
                pass  # rule 2 — never mask the real failure
        raise
    finally:
        if conn is not None:
            conn.close()

    ledger_note = ""
    entry = parse_ledger_entry(reply.text)
    if entry and not dry_run:
        ledger_note = append_ledger(config, *entry)
    elif entry:
        ledger_note = "(dry-run: ledger entry NOT appended)"

    print(reply.text)
    print(
        f"\n[{pass_name} pass: status={status_word}, iterations={reply.iterations}, "
        f"{reply.input_tokens} in / {reply.output_tokens} out"
        + (f", artifact={artifact}" if not dry_run else ", dry-run: no artifact")
        + (f"\n {ledger_note}" if ledger_note else "")
        + "]"
    )

    # Operator push: one line per real run. Dry-runs stay silent (same as they
    # withhold the artifact + ledger). A crashed pass never reaches here — that
    # path is the unit's OnFailure= pager.
    if not dry_run:
        _notify(_pass_summary(reply.text, status_word, entry, ledger_note))
        # Second message: the applyable half, so a proposal can be read and run
        # from a phone without opening the artifact. Opt out with
        # SYSADMIN_PUSH_PROPOSALS=0.
        if os.environ.get("SYSADMIN_PUSH_PROPOSALS", "1") != "0":
            if (push := _proposals_push(reply.text, artifact)):
                _notify(push)
