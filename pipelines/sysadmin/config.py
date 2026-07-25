"""Environment-driven config for the sysadmin agent runtime."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

# Until the operator creates /var/lib/sysadmin-agent (install block,
# deploy/systemd/README.md), proposals land in the gitignored state dir so the
# agent is usable pre-install. The systemd unit sets SYSADMIN_PROPOSALS_DIR to
# the real home.
DEFAULT_PROPOSALS_DIR = REPO_ROOT / "pipelines" / "sysadmin" / "state" / "proposals"
DEFAULT_LEDGER = REPO_ROOT / "docs" / "uzelhub-crew" / "sysadmin-ledger.md"


@dataclass
class SysadminConfig:
    anthropic_api_key: str
    postgres_dsn: str
    model: str
    max_cost_usd: float | None
    proposals_dir: Path
    ledger_path: Path
    paused: bool

    @classmethod
    def from_env(cls) -> "SysadminConfig":
        max_cost_raw = os.environ.get(
            "SYSADMIN_MAX_COST_USD", os.environ.get("PIPELINE_MAX_COST_USD", "")
        ).strip()
        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            postgres_dsn=os.environ.get(
                "POSTGRES_DSN",
                "postgresql://hvac_user@localhost:5432/ai_agent_platform",
            ),
            model=os.environ.get("SYSADMIN_MODEL", "claude-sonnet-5"),
            # Ambient agent: a hard default cap even when the env is silent.
            max_cost_usd=float(max_cost_raw) if max_cost_raw else 5.0,
            proposals_dir=Path(
                os.environ.get("SYSADMIN_PROPOSALS_DIR", str(DEFAULT_PROPOSALS_DIR))
            ),
            ledger_path=Path(os.environ.get("SYSADMIN_LEDGER", str(DEFAULT_LEDGER))),
            paused=bool(os.environ.get("SYSADMIN_PAUSED")),
        )
