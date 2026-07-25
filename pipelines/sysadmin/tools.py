"""The sysadmin agent's read-only hands — inspection tools for the reconciliation loop.

Same discipline as the Director's toolbox (pipelines/director/tools.py), wider
aperture: this agent audits the *host*, so its roots span /opt plus the system
config surfaces the design doc names (§Tools). The guardrail philosophy is
inherited unchanged — the prompt grants judgment; the tool enforces limits:

  - Reads are scoped to SYSADMIN_READ_ROOTS; `..`/symlink escapes are rejected.
  - Credential-shaped files are refused outright, and `/opt/_host/incidents/*`
    contents are refused by path (persona refusal #3: list, link, never ingest).
  - `run_cmd` is an allowlist of read-only inspection commands, exec'd without
    a shell; mutating verbs (docker start, systemctl restart, find -delete, …)
    are refused by construction, not by prompt discipline.
  - There is NO write tool at all. The Director carries one write exception in
    its toolbox (calendar_add); this agent's write exceptions (proposals dir,
    ledger) are exercised by the *runner* from the parsed report — the model's
    hands never hold a pen.

Output bounding is the Director's three-layer grep-bomb guard verbatim
(docs/director/devlog.md, 2026-06-29): bound at the pipe, clip per result,
budget per turn (the budget lives in the loop, agents/sysadmin_agent.py).
`journalctl` and `docker logs` are unbounded streams and this agent greps them
for a living — the pipe bound is what makes that safe.
"""
from __future__ import annotations

import os
import select
import subprocess
import time
from pathlib import Path
from typing import Any


MAX_TOOL_RESULT_CHARS = 40_000  # hard ceiling on ANY single tool result
MAX_READ_BYTES = 40_000
MAX_GREP_LINES = 120
MAX_GREP_LINE_CHARS = 300
MAX_DIR_ENTRIES = 200

_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".next", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}

_SECRET_EXACT = {
    ".env", ".netrc", ".git-credentials", ".pgpass",
    "credentials", "credentials.json", "secrets.json", "id_rsa", "id_ed25519",
    "authorized_keys", "known_hosts", "rclone.conf", "notify-telegram",
}
_SECRET_PREFIX = (".env.",)
_SECRET_SUFFIX = (".pem", ".key", ".pfx", ".p12", ".keystore", ".token")

_GIT_READONLY = {
    "log", "status", "diff", "show", "branch", "rev-parse", "ls-files", "ls-tree",
    "blame", "shortlog", "describe", "remote", "tag", "for-each-ref", "rev-list",
    "cat-file", "name-rev", "reflog",
}

# What the host-inspection shell may run. Keys are the only programs allowed;
# the value validates the args. Everything here is read-only on the box —
# the mutating verbs of the same programs are exactly what the safety
# constraints forbid (design §Safety: no systemctl start/restart, no
# docker compose up, no autonomous writes).
_SYSTEMCTL_VERBS = {
    "status", "cat", "show", "list-timers", "list-units", "list-unit-files",
    "list-dependencies", "is-enabled", "is-active", "is-failed", "show-environment",
}
_DOCKER_VERBS = {"ps", "inspect", "images", "logs", "version", "info"}
_DOCKER_LS_ONLY = {"volume", "network", "container", "system"}  # + {ls, ls, ls, df}
_FIND_FORBIDDEN = {"-delete", "-exec", "-execdir", "-ok", "-okdir", "-fprint",
                   "-fprint0", "-fprintf", "-fls"}
_PLAIN_ALLOWED = {"ls", "stat", "df", "du", "free", "uptime", "date", "id",
                  "whoami", "uname", "ss", "lsblk", "getent"}


def _validate_cmd(program: str, args: list[str]) -> str | None:
    """Return a refusal message, or None if the command is allowed."""
    if program == "systemctl":
        verb = next((a for a in args if not a.startswith("-")), "")
        if verb not in _SYSTEMCTL_VERBS:
            return (f"refused: systemctl verb {verb!r} is not read-only "
                    f"(allowed: {', '.join(sorted(_SYSTEMCTL_VERBS))}).")
        return None
    if program == "journalctl":
        return None  # read-only by nature; permission errors surface as findings
    if program == "docker":
        if not args:
            return "refused: docker needs a subcommand."
        if args[0] in _DOCKER_VERBS:
            return None
        if args[0] in _DOCKER_LS_ONLY and len(args) > 1 and args[1] in ("ls", "df", "inspect"):
            return None
        if args[0] == "compose" and len(args) > 1 and args[1] in ("ls",):
            return None
        return (f"refused: docker {' '.join(args[:2])!r} is not in the read-only "
                "allowlist (ps, inspect, images, logs, volume ls, network ls, compose ls, …).")
    if program == "find":
        bad = _FIND_FORBIDDEN.intersection(args)
        if bad:
            return f"refused: find with {sorted(bad)} can mutate — inspection only."
        return None
    if program == "crontab":
        if args != ["-l"] and args[:1] != ["-l"]:
            return "refused: only 'crontab -l' is allowed."
        return None
    if program in _PLAIN_ALLOWED:
        return None
    return (f"refused: {program!r} is not an allowed inspection command "
            f"(allowed: systemctl, journalctl, docker, find, crontab -l, "
            f"{', '.join(sorted(_PLAIN_ALLOWED))}).")


_PIPE_READ_LIMIT = 600_000
_PIPE_TIMEOUT = 15


def _bounded_output(cmd: list[str], limit: int = _PIPE_READ_LIMIT, timeout: int = _PIPE_TIMEOUT) -> str:
    """Run `cmd`, reading at most `limit` bytes within `timeout` seconds, then kill it.

    Bounds BOTH memory (never buffers more than `limit`) and time. stderr is
    merged so permission errors surface — for this agent a permission error is
    often the finding itself (e.g. journal-blind as claude).
    """
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as exc:
        return f"(could not run: {exc})"
    fd = proc.stdout.fileno()
    chunks: list[bytes] = []
    got = 0
    deadline = time.monotonic() + timeout
    try:
        while got < limit:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                break
            buf = os.read(fd, min(65536, limit - got))
            if not buf:
                break
            chunks.append(buf)
            got += len(buf)
    finally:
        proc.kill()
        try:
            proc.stdout.close()
            proc.wait(timeout=5)
        except Exception:
            pass
    return b"".join(chunks).decode("utf-8", errors="ignore")


# The reconciliation aperture: /opt (all projects + the _host layer) plus the
# system surfaces the design doc's tool table names. /etc/default is
# deliberately absent (notify-telegram token lives there); so is /root.
DEFAULT_READ_ROOTS = [
    "/opt",
    "/etc/systemd/system",
    "/etc/caddy",
    "/etc/logrotate.d",
    "/etc/cron.d",
    "/usr/local/sbin",
    "/var/log",
]


TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "run_cmd",
        "description": (
            "Run ONE read-only inspection command (no shell, no pipes): systemctl "
            "(status/cat/show/list-* verbs), journalctl, docker (ps/inspect/images/"
            "logs/volume ls/network ls), find (no -delete/-exec), crontab -l, ls, "
            "stat, df, du, free, uptime, date, id, ss, getent. Mutating verbs are "
            "refused. Output is bounded — narrow your query rather than dumping. "
            "A permission error is evidence too: report it, don't retry around it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "program": {"type": "string", "description": "The program, e.g. systemctl."},
                "args": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Arguments, e.g. ['list-timers','--all'].",
                },
            },
            "required": ["program"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file",
        "description": (
            "Read a UTF-8 text file (bounded prefix), or list a directory. Scoped to "
            "/opt, /etc/systemd/system, /etc/caddy, /etc/logrotate.d, /etc/cron.d, "
            "/usr/local/sbin, /var/log. Credential-shaped files are refused, and "
            "anything inside /opt/_host/incidents/ is refused by policy — you may "
            "list the incidents directory itself, never read its contents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path inside the read roots."}
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "grep",
        "description": (
            "Search file contents with an extended regex under a read root (or a "
            "subdirectory). Returns file:line:text, including untracked files. Use "
            "to locate where something is defined before reading it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "An extended (ERE) regex."},
                "path": {"type": "string", "description": "Absolute path under a read root."},
            },
            "required": ["pattern", "path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_git",
        "description": (
            "Run a READ-ONLY git command (log, status, diff, show, branch, …) in a "
            "repo under /opt. Mutating subcommands are refused. Ground truth over "
            "prose: verify what a doc claims against what git says."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute path of a repo under /opt."},
                "args": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Git args; first element must be a read-only subcommand.",
                },
            },
            "required": ["repo_path", "args"],
            "additionalProperties": False,
        },
    },
]


class ToolBox:
    """Executes the sysadmin agent's read-only tools, scoped to the read roots."""

    def __init__(self, read_roots: list[str] | None = None) -> None:
        self.roots = [Path(r).resolve() for r in (read_roots or DEFAULT_READ_ROOTS)]
        self.incidents_root = Path("/opt/_host/incidents").resolve()

    # --- guards -------------------------------------------------------------
    def _within_roots(self, raw: str) -> Path | None:
        if not raw:
            return None
        try:
            p = Path(raw).resolve()
        except Exception:
            return None
        for root in self.roots:
            if p == root or root in p.parents:
                return p
        return None

    @staticmethod
    def _looks_secret(p: Path) -> bool:
        n = p.name.lower()
        return (
            n in _SECRET_EXACT
            or n.startswith(_SECRET_PREFIX)
            or n.endswith(_SECRET_SUFFIX)
        )

    def _inside_incidents(self, p: Path) -> bool:
        return self.incidents_root in p.parents

    # --- dispatch -----------------------------------------------------------
    def dispatch(self, name: str, tool_input: dict[str, Any]) -> tuple[str, bool]:
        """Return (content, is_error). Never raises; never exceeds the result ceiling."""
        try:
            if name == "run_cmd":
                content, is_err = self._run_cmd(
                    tool_input.get("program", ""), tool_input.get("args", []) or []
                )
            elif name == "read_file":
                content, is_err = self._read_file(tool_input.get("path", ""))
            elif name == "grep":
                content, is_err = self._grep(
                    tool_input.get("pattern", ""), tool_input.get("path", "")
                )
            elif name == "run_git":
                content, is_err = self._run_git(
                    tool_input.get("repo_path", ""), tool_input.get("args", [])
                )
            else:
                return (f"unknown tool: {name}", True)
        except Exception as exc:
            return (f"tool error: {exc}", True)
        if len(content) > MAX_TOOL_RESULT_CHARS:
            content = content[:MAX_TOOL_RESULT_CHARS] + "\n…(result truncated to the tool-output limit)"
        return (content, is_err)

    def _run_cmd(self, program: str, args: Any) -> tuple[str, bool]:
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            return ("refused: args must be a list of strings.", True)
        if "/" in program:
            return ("refused: program must be a bare name resolved via PATH.", True)
        refusal = _validate_cmd(program, args)
        if refusal:
            return (refusal, True)
        out = _bounded_output([program, *args]).strip()
        return (out or "(no output)", False)

    def _read_file(self, raw: str) -> tuple[str, bool]:
        p = self._within_roots(raw)
        if not p:
            return ("refused: path is outside the read roots.", True)
        if self._inside_incidents(p):
            return ("refused: /opt/_host/incidents/ contents are forensic evidence — "
                    "list and link, never ingest (persona refusal #3).", True)
        if not p.exists():
            return (f"not found: {raw}", True)
        if p.is_dir():
            entries = sorted(
                c.name + ("/" if c.is_dir() else "")
                for c in p.iterdir()
                if c.name not in _SKIP_DIRS
            )[:MAX_DIR_ENTRIES]
            return (f"directory {p}:\n" + "\n".join(entries), False)
        if self._looks_secret(p):
            return ("refused: this looks like a secrets/credential file; I don't read those.", True)
        try:
            with p.open("rb") as fh:
                chunk = fh.read(MAX_READ_BYTES + 1)
        except Exception as exc:
            return (f"could not read: {exc}", True)
        head = chunk[:MAX_READ_BYTES]
        if b"\x00" in head:
            return ("refused: not a UTF-8 text file (binary?).", True)
        text = head.decode("utf-8", errors="ignore")
        if len(chunk) > MAX_READ_BYTES:
            text += "\n…(truncated — file is larger than the read limit)"
        return (text, False)

    def _grep(self, pattern: str, raw: str) -> tuple[str, bool]:
        if not pattern:
            return ("refused: empty pattern.", True)
        base = self._within_roots(raw)
        if not base:
            return ("refused: search path is outside the read roots.", True)
        if self._inside_incidents(base) or base == self.incidents_root:
            return ("refused: /opt/_host/incidents/ contents are forensic evidence.", True)
        cmd = ["grep", "-rIn", "--max-count=5"]
        cmd += [f"--exclude-dir={d}" for d in sorted(_SKIP_DIRS)]
        cmd += ["--exclude-dir=incidents"]
        cmd += ["-E", "--", pattern, str(base)]
        lines = _bounded_output(cmd).splitlines()
        if not lines:
            return ("(no matches)", False)
        clipped: list[str] = []
        for ln in lines[:MAX_GREP_LINES]:
            if len(ln) > MAX_GREP_LINE_CHARS:
                ln = ln[:MAX_GREP_LINE_CHARS] + " …(line truncated)"
            clipped.append(ln)
        more = (
            f"\n…({len(lines) - len(clipped)} more matching lines — narrow the pattern or path)"
            if len(lines) > len(clipped)
            else ""
        )
        return ("\n".join(clipped) + more, False)

    def _run_git(self, raw: str, args: Any) -> tuple[str, bool]:
        base = self._within_roots(raw)
        if not base or not str(base).startswith("/opt"):
            return ("refused: repo path must be under /opt.", True)
        if not isinstance(args, list) or not args or not all(isinstance(a, str) for a in args):
            return ("refused: args must be a non-empty list of strings.", True)
        if args[0] not in _GIT_READONLY:
            return (
                f"refused: '{args[0]}' is not an allowed read-only git subcommand "
                f"(allowed: {', '.join(sorted(_GIT_READONLY))}).",
                True,
            )
        text = _bounded_output(["git", "-C", str(base), *args]).strip()
        if len(text) > MAX_READ_BYTES:
            text = text[:MAX_READ_BYTES] + "\n…(truncated)"
        return (text or "(no output)", False)


def default_toolbox() -> ToolBox:
    return ToolBox()
