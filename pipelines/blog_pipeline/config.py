"""Environment-driven config for the blog pipeline runner."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PipelineConfig:
    source_repo_path: Path
    source_repo_name: str
    project_context: str

    ghost_admin_url: str
    ghost_admin_api_key: str

    postgres_dsn: str

    anthropic_api_key: str

    # Safety net: abort the run if cumulative LLM cost exceeds this. None disables.
    max_cost_usd: float | None

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        max_cost_raw = os.environ.get("PIPELINE_MAX_COST_USD", "").strip()
        max_cost = float(max_cost_raw) if max_cost_raw else None

        return cls(
            source_repo_path=Path(
                os.environ.get("PIPELINE_SOURCE_REPO", "/srv/predictor_ingest")
            ),
            source_repo_name=os.environ.get(
                "PIPELINE_SOURCE_NAME", "predictor_ingest"
            ),
            project_context=os.environ.get(
                "PIPELINE_PROJECT_CONTEXT",
                "predictor_ingest — RSS/signal pipeline feeding the predictor.",
            ),
            ghost_admin_url=os.environ.get(
                "GHOST_ADMIN_URL", "http://localhost:2368"
            ),
            ghost_admin_api_key=os.environ.get("GHOST_ADMIN_API_KEY", ""),
            postgres_dsn=os.environ.get(
                "POSTGRES_DSN",
                "postgresql://hvac_user@localhost:5432/ai_agent_platform",
            ),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            max_cost_usd=max_cost,
        )
