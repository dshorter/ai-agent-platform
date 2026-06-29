"""The Director's read-only hands — file / grep / git tools for the agentic loop.

Capability parity with the rest of the crew: the Director reads the box on demand
(open ADRs, backlogs, devlogs; grep for a symbol; pull fresh git state) instead of
working from a handed-over snapshot. Discipline, not capability, is the guardrail:

  - Reads are scoped to the registered project roots; `..` and symlink escapes are
    rejected (paths are resolved before the check).
  - Credential-shaped files (.env, *.pem, id_rsa, …) are refused outright —
    defense-in-depth behind the persona's "don't pull secrets into reasoning".
  - Only read-only git subcommands run.

There are deliberately NO write tools: the loop proposes writes as text for Dan to
approve. The ledger (a later slice) is the one thing the Director will own.

Output bounding — the three-layer guard against a single tool blowing the context
(`_bounded_output` at the pipe, the per-result ceiling in `dispatch`, and the
per-turn cap in the loop) — is documented in docs/director/ledger.md (2026-06-29).
"""
from __future__ import annotations

import os
import select
import subprocess
import time
from pathlib import Path
from typing import Any

from pipelines.director.registry import load_registry


# Bounded outputs keep the token cost of a single tool result sane. The universal
# ceiling matters: a single grep over scraped data (predictor_ingest stores raw HTML
# with 700k-char lines) once produced a 3.77M-token prompt and a 400. Every result is
# clipped to MAX_TOOL_RESULT_CHARS in dispatch, and grep clips per-line as well.
MAX_TOOL_RESULT_CHARS = 40_000  # hard ceiling on ANY single tool result (~10k tokens)
MAX_READ_BYTES = 40_000
MAX_GREP_LINES = 120
MAX_GREP_LINE_CHARS = 300  # clip long matched lines (minified/bundled/raw-HTML files)
MAX_DIR_ENTRIES = 200

# Never worth walking — noise, vendored deps, or secrets.
_SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".next", ".pytest_cache", ".mypy_cache", ".ruff_cache",
}

# Credential-shaped files — refuse to read (precise, not substring-broad, so a
# file like tokenizer.py or password_reset.md is NOT caught).
_SECRET_EXACT = {
    ".env", ".netrc", ".git-credentials", ".pgpass",
    "credentials", "credentials.json", "secrets.json", "id_rsa", "id_ed25519",
}
_SECRET_PREFIX = (".env.",)  # .env.local, .env.prod, …
_SECRET_SUFFIX = (".pem", ".key", ".pfx", ".p12", ".keystore")

# Read-only git subcommands the Director may run.
_GIT_READONLY = {
    "log", "status", "diff", "show", "branch", "rev-parse", "ls-files", "ls-tree",
    "blame", "shortlog", "describe", "remote", "tag", "for-each-ref", "rev-list",
    "cat-file", "name-rev", "reflog",
}

# How many bytes we ever pull off a subprocess pipe. The clip happens at the PIPE,
# not after the child finishes — `capture_output=True` buffers the whole stream first,
# which OOM-killed the process on a grep over scraped data. We read at most this, with
# a wall-clock deadline, then kill the child.
_PIPE_READ_LIMIT = 600_000
_PIPE_TIMEOUT = 15


def _bounded_output(cmd: list[str], limit: int = _PIPE_READ_LIMIT, timeout: int = _PIPE_TIMEOUT) -> str:
    """Run `cmd`, reading at most `limit` bytes within `timeout` seconds, then kill it.

    Bounds BOTH memory (never buffers more than `limit`) and time (a slow no-match scan
    over a huge tree can't hang the loop). stderr is merged so git errors surface.
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
                break  # wall-clock timeout
            buf = os.read(fd, min(65536, limit - got))
            if not buf:
                break  # EOF — child finished
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


TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "read_file",
        "description": (
            "Read a UTF-8 text file from a registered project, or list the entries if "
            "the path is a directory. Call this to verify what a doc actually says — an "
            "ADR, BACKLOG.md, a devlog, a README — before you rank or route. Paths must "
            "be inside a registered project root; credential files are refused."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path inside a registered project root.",
                }
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "grep",
        "description": (
            "Search file contents with an extended regular expression across a project "
            "root (or a subdirectory of one). Returns matching lines as file:line:text, "
            "and searches the working tree INCLUDING untracked files. Call this to locate "
            "where something is defined or mentioned before you read the file."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "An extended (ERE) regex."},
                "path": {
                    "type": "string",
                    "description": "Absolute path of a project root or a subdirectory within one.",
                },
            },
            "required": ["pattern", "path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_git",
        "description": (
            "Run a READ-ONLY git command in a registered project to pull fresh ground "
            "truth (log, status, diff, show, branch, rev-parse, ls-files, blame, …). "
            "Mutating subcommands are refused. This is how you verify state instead of "
            "trusting a stale snapshot."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "project_path": {
                    "type": "string",
                    "description": "Absolute path of a registered project root.",
                },
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Git args, e.g. ['log','--oneline','-n','20']. The first element "
                        "must be a read-only subcommand."
                    ),
                },
            },
            "required": ["project_path", "args"],
            "additionalProperties": False,
        },
    },
]


class ToolBox:
    """Executes the Director's read-only tools, scoped to a set of project roots."""

    def __init__(self, allowed_roots: list[Path]) -> None:
        self.roots = [r.resolve() for r in allowed_roots]

    # --- guards -------------------------------------------------------------
    def _within_roots(self, raw: str) -> Path | None:
        """Resolve `raw` (following symlinks) and return it only if under a root."""
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

    # --- dispatch -----------------------------------------------------------
    def dispatch(self, name: str, tool_input: dict[str, Any]) -> tuple[str, bool]:
        """Return (content, is_error). Never raises, and never exceeds the result ceiling."""
        try:
            if name == "read_file":
                content, is_err = self._read_file(tool_input.get("path", ""))
            elif name == "grep":
                content, is_err = self._grep(
                    tool_input.get("pattern", ""), tool_input.get("path", "")
                )
            elif name == "run_git":
                content, is_err = self._run_git(
                    tool_input.get("project_path", ""), tool_input.get("args", [])
                )
            else:
                return (f"unknown tool: {name}", True)
        except Exception as exc:  # never crash the loop on a bad tool call
            return (f"tool error: {exc}", True)
        # Universal chokepoint — guarantees no single result can blow the context.
        if len(content) > MAX_TOOL_RESULT_CHARS:
            content = content[:MAX_TOOL_RESULT_CHARS] + "\n…(result truncated to the tool-output limit)"
        return (content, is_err)

    def _read_file(self, raw: str) -> tuple[str, bool]:
        p = self._within_roots(raw)
        if not p:
            return ("refused: path is outside the registered project roots.", True)
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
                chunk = fh.read(MAX_READ_BYTES + 1)  # read a bounded prefix, not the whole file
        except Exception as exc:
            return (f"could not read: {exc}", True)
        head = chunk[:MAX_READ_BYTES]
        if b"\x00" in head:  # NUL byte => binary, don't dump it into the prompt
            return ("refused: not a UTF-8 text file (binary?).", True)
        text = head.decode("utf-8", errors="ignore")  # ignore avoids splitting a multibyte char
        if len(chunk) > MAX_READ_BYTES:
            text += "\n…(truncated — file is larger than the read limit)"
        return (text, False)

    def _grep(self, pattern: str, raw: str) -> tuple[str, bool]:
        if not pattern:
            return ("refused: empty pattern.", True)
        base = self._within_roots(raw)
        if not base:
            return ("refused: search path is outside the registered project roots.", True)
        cmd = ["grep", "-rIn", "--max-count=5"]
        cmd += [f"--exclude-dir={d}" for d in sorted(_SKIP_DIRS)]
        cmd += ["-E", "--", pattern, str(base)]
        lines = _bounded_output(cmd).splitlines()
        if not lines:
            return ("(no matches)", False)
        clipped: list[str] = []
        for ln in lines[:MAX_GREP_LINES]:
            if len(ln) > MAX_GREP_LINE_CHARS:
                # one matched line can be a whole minified bundle or a 700k-char raw-HTML row
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
        if not base:
            return ("refused: project path is outside the registered project roots.", True)
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
    """A ToolBox scoped to every registered project root."""
    return ToolBox([Path(p.path) for p in load_registry()])
