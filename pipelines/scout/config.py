"""Environment-driven config for the Scout runtime.

The synthesis model is deliberately an env var (NEWSROOM §Model tiers: "make
the synthesis model an env var, run one ambient pass each through Sonnet and
Fable, let lead quality decide"). Fable 5 is the plan; the A/B is the check.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path


_HERE = Path(__file__).resolve().parent

_DEFAULT_ROW_BUDGET = 150


def _legacy_budget() -> int:
    """Honour a hand-set SCOUT_WALK_PAGES rather than silently ignoring it.

    The knob was renamed when it turned out to be sizing the plate, not the
    call. Anyone who had tuned the old one deliberately should get what they
    asked for and a line saying it moved — a silently ignored env var is the
    kind of thing that gets diagnosed months later.
    """
    pages = os.environ.get("SCOUT_WALK_PAGES")
    if not pages:
        return _DEFAULT_ROW_BUDGET
    rows = int(os.environ.get("SCOUT_PAGE_ROWS", "150")) * int(pages)
    logging.getLogger("uzelhub_crew.scout.config").warning(
        "SCOUT_WALK_PAGES=%s is retired — using SCOUT_PASS_ROW_BUDGET=%d. "
        "Set the new var directly; note that a bigger plate mines THINNER "
        "(docs/uzelhub-crew/scout-mining-economics.md).",
        pages, rows,
    )
    return rows


@dataclass
class ScoutConfig:
    postgres_dsn: str
    anthropic_api_key: str
    walk_model: str            # cheap, high-volume triage (the marketer's Haiku split, inherited)
    synthesis_model: str       # the "link 16 things" leap — premium by design
    synthesis_fallback: str    # used once if synthesis stops with stop_reason=refusal
    page_rows: int             # log rows per triage page (bounded chunk per NEWSROOM cursor rules)
    pass_row_budget: int       # TOTAL rows one --pass may walk (see below)
    roam_iterations: int       # synthesis tool round-trips before the pitch is forced
    max_cost_usd: float        # soft cap across one pass
    logs_dir: Path             # Claude Code session logs root (needs root to read)
    codex_logs_dir: Path       # Codex rollout logs (work-machine corpus, pulled from gdrive:)
    state_dir: Path            # cursor + map — external, inspectable, warm-bootable
    leads_path: Path           # the leads ledger (the Editor's queue)
    # Last, with a default, so every existing construction keeps working.
    pitch_digest_chars: int = 240  # chars of each past pitch shown to synthesis
    # The estate's repos, as git ore. Commit messages carry the RESOLVED
    # register that session logs structurally cannot — what was decided and
    # why, written after — which is the register the copy has been missing.
    git_repos: tuple[Path, ...] = ()

    @classmethod
    def from_env(cls) -> "ScoutConfig":
        return cls(
            postgres_dsn=os.environ.get(
                "POSTGRES_DSN",
                "postgresql://hvac_user@localhost:5432/ai_agent_platform",
            ),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            walk_model=os.environ.get("SCOUT_WALK_MODEL", "claude-haiku-4-5-20251001"),
            # Fable → Sonnet 5, 2026-09-03, on measured cost rather than the
            # price list. 39 Fable synthesis calls averaged $1.3274 and totalled
            # $51.77, against $0.75 for all 106 walk calls put together — 187x
            # per call. Worse, it grew: $0.448/call the week of 07-06 to
            # $1.847 by 08-10, because the dedup payload rides in this prompt
            # and scales with the leads ledger (scout-mining-economics.md).
            # NEWSROOM §Model tiers called this "pennies per pass"; it was not,
            # and both premises behind that ("ambient, weekly-ish" — it went
            # daily; "low-token" — $1.33 on a $10/$50 model is not low-token)
            # were false. The QUALITY argument for Fable is untouched and still
            # unmeasured: spend on it where it demonstrably pays, per run, with
            # SCOUT_SYNTHESIS_MODEL — do not pay 5x by default on an untested
            # assumption.
            synthesis_model=os.environ.get("SCOUT_SYNTHESIS_MODEL", "claude-sonnet-5"),
            synthesis_fallback=os.environ.get("SCOUT_SYNTHESIS_FALLBACK", "claude-opus-5"),
            page_rows=int(os.environ.get("SCOUT_PAGE_ROWS", "150")),
            # 150 rows, not the 450 that walk_pages=3 x page_rows=150 gave.
            # Output is homeostatic at ~13 leads a pass no matter what goes in
            # (scout-mining-economics.md), so conversion runs 0.18 leads per
            # jewel on a 450-row plate and ~1.0 on a small one: MORE ore per
            # pass mines THINNER. The plate is sized so the machine's natural
            # output consumes what the walk finds. page_rows stays a separate
            # concern — how big one Haiku call is — instead of doing double
            # duty as the pass cap.
            pass_row_budget=int(
                os.environ.get("SCOUT_PASS_ROW_BUDGET", str(_legacy_budget()))
            ),
            roam_iterations=int(os.environ.get("SCOUT_ROAM_ITERATIONS", "6")),
            max_cost_usd=float(os.environ.get("SCOUT_MAX_COST_USD", "2.0")),
            # The already-pitched dedup payload is the DOMINANT term in the
            # synthesis prompt — bigger than the jewels it reasons over, and it
            # grows every time a lead is filed, forever, because dedup memory
            # can never be pruned. Measured 2026-09-04 over 477 leads: full
            # text is 279,744 chars (~70K tokens); at 240 it is 130,815
            # (~33K), a 53% cut with every digest still a complete first
            # sentence. Shorter limits cut more and start truncating
            # mid-thought, and dedup quality is worth more than the last 12%.
            # Set to 0/None-equivalent by passing a large number for the
            # pre-2026-09 full-text behaviour. See leads.load_pitched.
            pitch_digest_chars=int(os.environ.get("SCOUT_PITCH_DIGEST_CHARS", "240")),
            git_repos=tuple(
                Path(p) for p in os.environ.get(
                    "SCOUT_GIT_REPOS",
                    "/opt/ai-agent-platform:/opt/predictor_ingest:/opt/uzelhub-web"
                    ":/opt/server-maintenance:/opt/_host",
                ).split(":") if p
            ),
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
