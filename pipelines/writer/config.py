"""Environment-driven config for the Writer runtime.

The seat is the house Sonnet default (NEWSROOM §Model tiers / writer-persona
§The seat): the Fable asymmetry inverts at this desk — everything filters the
Writer's bad copy, so quality rides on the exemplars in the bottle, not raw
IQ. Env-var'd like its siblings' seats so the choice stays a config, not a
commit.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent

# v1 register→profile routing: the note leg only. New registers add rows
# here (a sink profile is data), never a new agent.
REGISTER_PROFILES = {"note": "man-page-dry"}


@dataclass
class WriterConfig:
    postgres_dsn: str
    anthropic_api_key: str
    model: str                 # the desk's seat — house Sonnet default
    fallback_model: str        # used once if a draft stops with stop_reason=refusal
    roam_iterations: int       # convergent-roam tool round-trips before the draft is forced
    max_cost_usd: float        # soft cap for one assignment
    leads_path: Path           # the Scout's ledger — the Writer reads, never writes
    voice_dir: Path            # the bottle: voice/<profile>/{samples,moves.md}
    state_dir: Path            # drafts park here, gitignored — a push is a publish

    @property
    def drafts_dir(self) -> Path:
        return self.state_dir / "drafts"

    @classmethod
    def from_env(cls) -> "WriterConfig":
        return cls(
            postgres_dsn=os.environ.get(
                "POSTGRES_DSN",
                "postgresql://hvac_user@localhost:5432/ai_agent_platform",
            ),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            model=os.environ.get("WRITER_MODEL", "claude-sonnet-5"),
            fallback_model=os.environ.get("WRITER_FALLBACK_MODEL", "claude-opus-4-8"),
            roam_iterations=int(os.environ.get("WRITER_ROAM_ITERATIONS", "6")),
            max_cost_usd=float(os.environ.get("WRITER_MAX_COST_USD", "2.0")),
            leads_path=Path(
                os.environ.get(
                    "SCOUT_LEADS_PATH",
                    str(_REPO / "pipelines" / "scout" / "state" / "leads.yaml"),
                )
            ),
            voice_dir=Path(os.environ.get("WRITER_VOICE_DIR", str(_REPO / "voice"))),
            # Drafts are session-log-derived and UNPUBLISHED by definition —
            # they live where a push can't reach (origin is public), and only
            # cross into uzelhub-web's tracked notes.json after the scrub AND
            # the Editor's copyDraft approval.
            state_dir=Path(os.environ.get("WRITER_STATE_DIR", str(_HERE / "state"))),
        )
