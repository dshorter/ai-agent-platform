"""Structural selftest — the guard rails, exercised without an API call.

The grep-bomb postmortem's open item was "the toolbox guards are pure functions
begging for fast units." For this agent they exist from day one: every refusal
the design doc promises is asserted here, so `--selftest` is the on-box CI gate
before any commit (WORKFLOW.md: on-box checks ARE the CI for this repo).
"""
from __future__ import annotations

from pipelines.sysadmin.run import PASSES, parse_ledger_entry
from pipelines.sysadmin.tools import ToolBox, _validate_cmd


def run_selftest() -> int:
    box = ToolBox()
    failures: list[str] = []

    def check(label: str, ok: bool) -> None:
        print(("  ok    " if ok else "  FAIL  ") + label)
        if not ok:
            failures.append(label)

    print("toolbox guards:")
    out, err = box.dispatch("read_file", {"path": "/etc/shadow"})
    check("path outside roots refused", err and "outside" in out)
    out, err = box.dispatch("read_file", {"path": "/opt/ai-agent-platform/.env"})
    check(".env refused as secret", err and "secret" in out.lower())
    out, err = box.dispatch("read_file", {"path": "/opt/_host/incidents/x/notes.md"})
    check("incidents contents refused", err and "forensic" in out)
    out, err = box.dispatch("read_file", {"path": "/opt/../etc/passwd"})
    check("dot-dot escape refused", err)
    out, err = box.dispatch("run_git", {"repo_path": "/opt/ai-agent-platform",
                                        "args": ["push", "origin", "main"]})
    check("mutating git refused", err and "read-only" in out)
    out, err = box.dispatch("run_cmd", {"program": "systemctl", "args": ["restart", "ghost"]})
    check("systemctl restart refused", err)
    out, err = box.dispatch("run_cmd", {"program": "docker", "args": ["compose", "up", "-d"]})
    check("docker compose up refused", err)
    out, err = box.dispatch("run_cmd", {"program": "find",
                                        "args": ["/opt", "-name", "*.tmp", "-delete"]})
    check("find -delete refused", err)
    out, err = box.dispatch("run_cmd", {"program": "rm", "args": ["-rf", "/opt"]})
    check("unlisted program refused", err)
    out, err = box.dispatch("run_cmd", {"program": "/usr/bin/docker", "args": ["ps"]})
    check("absolute-path program refused", err)
    check("read-only systemctl allowed", _validate_cmd("systemctl", ["list-timers", "--all"]) is None)
    check("docker ps allowed", _validate_cmd("docker", ["ps", "-a"]) is None)
    out, err = box.dispatch("read_file", {"path": "/opt/_host/README.md"})
    check("README readable", not err and "System Layout" in out)

    print("report parsing:")
    sample = ("## Status: FINDINGS\n## Findings\n1. x\n## Proposals\nnone this pass.\n"
              "## Would-not\n- y\n## Ledger entry\nTITLE: Test title\nBody line.\nReceipts: z.\n")
    entry = parse_ledger_entry(sample)
    check("ledger entry parsed", entry == ("Test title", "Body line.\nReceipts: z."))
    check("no-entry report yields None", parse_ledger_entry("## Status: CLEAN\n") is None)
    check("daily charter registered", "daily" in PASSES)

    print(f"\nselftest: {'PASS' if not failures else 'FAIL'} "
          f"({len(failures)} failure(s))")
    return 1 if failures else 0
