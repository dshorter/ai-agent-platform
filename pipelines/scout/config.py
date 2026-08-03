"""Environment-driven config for the Scout runtime.

The synthesis model is deliberately an env var (NEWSROOM §Model tiers: "make
the synthesis model an env var, run one ambient pass each through Sonnet and
Fable, let lead quality decide"). Fable 5 is the plan; the A/B is the check.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


_HERE = Path(__file__).resolve().parent


@dataclass
class ScoutConfig:
    postgres_dsn: str
    anthropic_api_key: str
    walk_model: str            # cheap, high-volume triage (the marketer's Haiku split, inherited)
    synthesis_model: str       # the "link 16 things" leap — premium by design
    synthesis_fallback: str    # used once if synthesis stops with stop_reason=refusal
    page_rows: int             # log rows per triage page (bounded chunk per NEWSROOM cursor rules)
    walk_pages: int            # max triage pages per pass
    roam_iterations: int       # synthesis tool round-trips before the pitch is forced
    max_cost_usd: float        # soft cap across one pass
    logs_dir: Path             # Claude Code session logs root (needs root to read)
    codex_logs_dir: Path       # Codex rollout logs (work-machine corpus, pulled from gdrive:)
    state_dir: Path            # cursor + map — external, inspectable, warm-bootable
    leads_path: Path           # the leads ledger (the Editor's queue)

    @classmethod
    def from_env(cls) -> "ScoutConfig":
        return cls(
            postgres_dsn=os.environ.get(
                "POSTGRES_DSN",
                "postgresql://hvac_user@localhost:5432/ai_agent_platform",
            ),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            walk_model=os.environ.get("SCOUT_WALK_MODEL", "claude-haiku-4-5-20251001"),
            synthesis_model=os.environ.get("SCOUT_SYNTHESIS_MODEL", "claude-fable-5"),
            synthesis_fallback=os.environ.get("SCOUT_SYNTHESIS_FALLBACK", "claude-opus-4-8"),
            page_rows=int(os.environ.get("SCOUT_PAGE_ROWS", "150")),
            walk_pages=int(os.environ.get("SCOUT_WALK_PAGES", "3")),
            roam_iterations=int(os.environ.get("SCOUT_ROAM_ITERATIONS", "6")),
            max_cost_usd=float(os.environ.get("SCOUT_MAX_COST_USD", "2.0")),
            # Sessions moved to the claude user on 2026-07-16 (root→claude
            # consolidation); root's dir kept stale pre-switchover copies with
            # the SAME session ids, so ingest looked alive while everything
            # new went unread — found 2026-08-03, 27 of 41 sessions missing.
            logs_dir=Path(os.environ.get("SCOUT_LOGS_DIR", "/home/claude/.claude/projects")),
            codex_logs_dir=Path(
                os.environ.get("SCOUT_CODEX_LOGS_DIR", "/root/staging/codex-logs/logs")
            ),
            state_dir=Path(os.environ.get("SCOUT_STATE_DIR", str(_HERE / "state"))),
            # In the STATE dir, deliberately outside the committed tree: origin is a
            # PUBLIC repo, and leads are transcript-derived — the redaction gate
            # (NEWSROOM, absolute) forbids publishing them unscrubbed. The queue is
            # local; publication happens only after scrub + Editor approval.
            leads_path=Path(
                os.environ.get(
                    "SCOUT_LEADS_PATH", str(_HERE / "state" / "leads.yaml")
                )
            ),
        )
