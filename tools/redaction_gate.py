#!/usr/bin/env python3
"""Redaction gate — the same detector, pointed at what is about to be committed.

`pipelines/writer/redaction.py` guards the PUBLISHING path: a Writer draft
crossing into notes.json, whose working tree is the live apex docroot. It has
never guarded the path that is used far more often — a doc or a script staged
straight into this repo, which is PUBLIC. A push is a publish, and on
2026-08-23 four docs drawn from an employer-gated corpus were committed with
nothing but hand-typed greps between them and the internet. They were clean.
That is not a control.

Two detectors, because the risks are different shapes:

  * SECRETS AND PII — reuses redaction.scan() unchanged. Keys, private keys,
    DB credential URLs, capability URLs, home paths, emails, public IPs.
  * EMPLOYER-GATE VOCABULARY — a term list. NEWSROOM's employer gate says
    day-job material publishes only technique-forward and application-
    anonymous; the product names are the part that breaks anonymity.

**The vocabulary deliberately lives outside this repo** (default
/opt/_host/redaction-gate/, which has no remote). A file in a public repo
listing employer product names is the disclosure it was written to prevent.

Findings are dismissed by `kind:text` key in allow.txt — the same stable handle
redaction.Finding was given so a verdict survives a rebuild. Dismissing is a
human act with a reason, never an auto-scrub: a scrubber that silently rewrites
buys false confidence, misses something, and is trusted anyway.

**The hook path is diff-aware (2026-09-01).** A staged finding is suppressed
when the same `kind:text` key already appears in HEAD's version of that same
file: content already in a public tree is not a leak this commit introduces,
and blocking on it froze five finished changes for weeks (the detector's own
test fixtures re-blocked the file every time a rule was added). A NEW finding
anywhere — including a new fixture, including in a new file — still blocks and
still wants one deliberate look. Suppressed counts are reported, never silent.
`--all` and explicit paths stay full-strength: an audit answers "what is in
the tree", the hook answers "what is this commit adding".

    tools/redaction_gate.py                 # scan what is staged (the hook path)
    tools/redaction_gate.py --all           # scan every tracked file
    tools/redaction_gate.py FILE [FILE...]  # scan specific paths
    tools/redaction_gate.py --install       # install as .git/hooks/pre-commit

`git commit --no-verify` bypasses it. That is deliberate and correct — the
operator's pen overrides the machine, as everywhere else in this shop.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from pipelines.writer.redaction import Finding, scan  # noqa: E402

CONFIG_DIR = Path(os.environ.get("REDACTION_GATE_CONFIG", "/opt/_host/redaction-gate"))

# Binary and generated things a text detector has no business reading, plus the
# gate's own report format. Kept small on purpose: every exclusion is a place a
# leak could hide, so the bar for adding one is "a text scan is meaningless
# here", not "this file is noisy".
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf",
                 ".woff", ".woff2", ".ttf", ".otf", ".zip", ".gz", ".tar",
                 ".pyc", ".so", ".bin", ".ics"}
MAX_BYTES = 2_000_000


def _load_lines(name: str) -> list[str]:
    path = CONFIG_DIR / name
    if not path.exists():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip() if not raw.lstrip().startswith("#") else ""
        if line:
            out.append(line)
    return out


def term_pattern(terms: list[str]) -> re.Pattern | None:
    """Word-boundary alternation, case-insensitive, longest-first so a
    multi-word term wins over a substring of itself."""
    if not terms:
        return None
    parts = [re.escape(t).replace(r"\ ", r"\s+") for t in sorted(terms, key=len, reverse=True)]
    return re.compile(r"(?<![\w-])(?:" + "|".join(parts) + r")(?![\w-])", re.IGNORECASE)


def scan_text(text: str, terms: re.Pattern | None) -> list[Finding]:
    found = list(scan(text))
    if terms:
        found += [
            Finding("employer-gate", m.group(0), m.start(), m.end(),
                    "day-job identifier; NEWSROOM's employer gate allows only "
                    "technique-forward, application-anonymous publication")
            for m in terms.finditer(text)
        ]
    return sorted(found, key=lambda f: f.start)


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=_REPO, capture_output=True, text=True, check=True,
    )
    return [p for p in out.stdout.splitlines() if p.strip()]


def staged_content(path: str) -> str | None:
    """The blob as STAGED, not as it sits in the working tree. They differ
    whenever someone edits after `git add`, and the staged version is the one
    about to become public."""
    out = subprocess.run(["git", "show", f":{path}"], cwd=_REPO,
                         capture_output=True, check=False)
    if out.returncode != 0:
        return None
    try:
        return out.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None  # binary; nothing a text detector can say about it


def head_content(path: str) -> str | None:
    """The blob as it sits in HEAD — the baseline for "already public".
    None for a file HEAD does not have (or before the first commit), which
    makes every finding in it new, which is the conservative answer."""
    out = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=_REPO,
                         capture_output=True, check=False)
    if out.returncode != 0:
        return None
    try:
        return out.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check(paths: list[str], read, terms, allow: set[str],
          baseline=None) -> tuple[list[tuple], int]:
    """Returns (blocking hits, count suppressed as already-in-baseline).

    `baseline` is a read-alike returning the prior version of a path, or None
    for no diff-awareness. Suppression is per-file: a key in HEAD's copy of
    a DIFFERENT file does not excuse this one."""
    hits, suppressed = [], 0
    for path in paths:
        if Path(path).suffix.lower() in SKIP_SUFFIXES:
            continue
        text = read(path)
        if text is None or len(text) > MAX_BYTES:
            continue
        prior: set[str] = set()
        if baseline is not None:
            prior_text = baseline(path)
            if prior_text is not None and len(prior_text) <= MAX_BYTES:
                prior = {f.key for f in scan_text(prior_text, terms)}
        for f in scan_text(text, terms):
            if f.key in allow:
                continue
            if f.key in prior:
                suppressed += 1
                continue
            hits.append((path, line_of(text, f.start), f))
    return hits, suppressed


HOOK = """#!/bin/sh
# Installed by tools/redaction_gate.py. This repo is PUBLIC: a push is a
# publish. Bypass with `git commit --no-verify` when you have looked and are
# sure — that is the operator's pen, not a loophole.
exec "{python}" "{gate}"
"""


def install() -> int:
    hooks = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=_REPO,
                           capture_output=True, text=True, check=True).stdout.strip()
    hook = (_REPO / hooks / "pre-commit") if not Path(hooks).is_absolute() else Path(hooks) / "pre-commit"
    hook.parent.mkdir(parents=True, exist_ok=True)
    if hook.exists():
        backup = hook.with_suffix(".pre-redaction-gate")
        # Never silently discard someone else's hook.
        if not backup.exists():
            backup.write_text(hook.read_text())
            print(f"existing hook backed up -> {backup}")
    python = sys.executable or "python3"
    hook.write_text(HOOK.format(python=python, gate=Path(__file__).resolve()))
    hook.chmod(0o755)
    print(f"installed {hook}")
    print("bypass with: git commit --no-verify")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="specific files (default: what is staged)")
    ap.add_argument("--all", action="store_true", help="scan every tracked file")
    ap.add_argument("--install", action="store_true", help="install as the pre-commit hook")
    args = ap.parse_args(argv)

    if args.install:
        return install()

    terms = term_pattern(_load_lines("terms.txt"))
    allow = set(_load_lines("allow.txt"))
    if terms is None:
        # Loud, not fatal: the secrets half still works, but someone should know
        # the vocabulary half is not running.
        print(f"redaction-gate: no terms.txt under {CONFIG_DIR} — "
              "employer-gate checking is OFF", file=sys.stderr)

    baseline = None
    if args.paths:
        paths, read = args.paths, lambda p: Path(p).read_text(encoding="utf-8", errors="replace")
    elif args.all:
        out = subprocess.run(["git", "ls-files"], cwd=_REPO, capture_output=True,
                             text=True, check=True)
        paths = out.stdout.splitlines()
        read = lambda p: (_REPO / p).read_text(encoding="utf-8", errors="replace")  # noqa: E731
    else:
        paths, read, baseline = staged_files(), staged_content, head_content

    hits, suppressed = check(paths, read, terms, allow, baseline=baseline)
    already = (f"; {suppressed} finding(s) already in HEAD — not this commit's leak"
               if suppressed else "")
    if not hits:
        print(f"redaction-gate: clean ({len(paths)} file(s){already})")
        return 0

    print(f"\nredaction-gate: {len(hits)} unresolved finding(s) — commit BLOCKED"
          f"{already}\n", file=sys.stderr)
    for path, line, f in hits:
        print(f"  {path}:{line}", file=sys.stderr)
        print(f"    [{f.kind}] {f.text[:80]}", file=sys.stderr)
        print(f"    {f.why}", file=sys.stderr)
        print(f"    dismiss with: echo '{f.key}' >> {CONFIG_DIR}/allow.txt", file=sys.stderr)
        print(file=sys.stderr)
    print("Fix the file, or dismiss the finding with a reason. "
          "`git commit --no-verify` overrides.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
