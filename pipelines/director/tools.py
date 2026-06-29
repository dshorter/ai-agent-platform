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
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from pipelines.director.registry import load_registry


# Bounded outputs keep the token cost of a single read sane.
MAX_READ_BYTES = 60_000
MAX_GREP_LINES = 120
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
        """Return (content, is_error). Never raises — a tool error feeds back to the model."""
        try:
            if name == "read_file":
                return self._read_file(tool_input.get("path", ""))
            if name == "grep":
                return self._grep(tool_input.get("pattern", ""), tool_input.get("path", ""))
            if name == "run_git":
                return self._run_git(tool_input.get("project_path", ""), tool_input.get("args", []))
            return (f"unknown tool: {name}", True)
        except Exception as exc:  # never crash the loop on a bad tool call
            return (f"tool error: {exc}", True)

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
            raw_bytes = p.read_bytes()
        except Exception as exc:
            return (f"could not read: {exc}", True)
        try:
            text = raw_bytes[:MAX_READ_BYTES].decode("utf-8")
        except UnicodeDecodeError:
            return ("refused: not a UTF-8 text file (binary?).", True)
        if len(raw_bytes) > MAX_READ_BYTES:
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
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        except Exception as exc:
            return (f"grep error: {exc}", True)
        lines = (out.stdout or "").splitlines()
        if not lines:
            return ("(no matches)", False)
        shown = lines[:MAX_GREP_LINES]
        more = (
            f"\n…({len(lines) - len(shown)} more matching lines — narrow the pattern or path)"
            if len(lines) > len(shown)
            else ""
        )
        return ("\n".join(shown) + more, False)

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
        try:
            out = subprocess.run(
                ["git", "-C", str(base), *args],
                capture_output=True, text=True, timeout=20,
            )
        except Exception as exc:
            return (f"git error: {exc}", True)
        text = (out.stdout or out.stderr).strip()
        if len(text) > MAX_READ_BYTES:
            text = text[:MAX_READ_BYTES] + "\n…(truncated)"
        return (text or "(no output)", False)


def default_toolbox() -> ToolBox:
    """A ToolBox scoped to every registered project root."""
    return ToolBox([Path(p.path) for p in load_registry()])
