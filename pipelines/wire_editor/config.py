"""Environment-driven config for the Wire Editor runtime.

Two seats: the wire desk (house Sonnet default — triage is judgment over a
big haystack, exactly Sonnet's price/perf pocket) and the chief's shadow
seat, which deliberately follows DIRECTOR_MODEL so the shadow verdicts are
produced by the same brain that would inherit gate ① — concordance measured
against any other model would be measuring the wrong candidate.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent


@dataclass
class WireEditorConfig:
    postgres_dsn: str
    anthropic_api_key: str
    wire_model: str
    chief_model: str
    leads_path: Path
    state_dir: Path

    @property
    def proposals_dir(self) -> Path:
        return self.state_dir / "proposals"

    @classmethod
    def from_env(cls) -> "WireEditorConfig":
        return cls(
            postgres_dsn=os.environ.get(
                "POSTGRES_DSN",
                "postgresql://hvac_user@localhost:5432/ai_agent_platform",
            ),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            wire_model=os.environ.get("WIRE_EDITOR_MODEL", "claude-sonnet-5"),
            chief_model=os.environ.get("DIRECTOR_MODEL", "claude-sonnet-5"),
            leads_path=Path(
                os.environ.get(
                    "SCOUT_LEADS_PATH",
                    str(_REPO / "pipelines" / "scout" / "state" / "leads.yaml"),
                )
            ),
            # Proposals quote pitch material (session-log-derived, unscrubbed)
            # — gitignored for the same reason drafts are: a push is a publish.
            state_dir=Path(os.environ.get("WIRE_EDITOR_STATE_DIR", str(_HERE / "state"))),
        )
