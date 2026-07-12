"""Environment-driven config for the Director runtime."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class DirectorConfig:
    telegram_token: str
    allowed_user_id: int | None  # whitelist; None = not set (listener refuses to run live)
    postgres_dsn: str
    anthropic_api_key: str
    model: str
    max_cost_usd: float | None
    poll_timeout: int  # long-poll seconds for getUpdates

    @classmethod
    def from_env(cls) -> "DirectorConfig":
        allowed_raw = os.environ.get("DIRECTOR_TELEGRAM_ALLOWED_USER", "").strip()
        max_cost_raw = os.environ.get(
            "DIRECTOR_MAX_COST_USD", os.environ.get("PIPELINE_MAX_COST_USD", "")
        ).strip()
        return cls(
            telegram_token=os.environ.get("DIRECTOR_TELEGRAM_TOKEN", ""),
            allowed_user_id=int(allowed_raw) if allowed_raw else None,
            postgres_dsn=os.environ.get(
                "POSTGRES_DSN",
                "postgresql://hvac_user@localhost:5432/ai_agent_platform",
            ),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            model=os.environ.get("DIRECTOR_MODEL", "claude-sonnet-5"),
            max_cost_usd=float(max_cost_raw) if max_cost_raw else None,
            poll_timeout=int(os.environ.get("DIRECTOR_POLL_TIMEOUT", "30")),
        )
