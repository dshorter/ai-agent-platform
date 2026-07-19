"""The voice bottle — convention-path loader.

voice/<profile>/samples/  — exemplars (harvested or seeded); samples carry
                            the voice.
voice/<profile>/moves.md  — the named-move list, deliberately thin.

A new voice is authored by dropping samples — no code. The loader just
assembles the profile into one prompt block; it imposes no schema on the
samples (a .json sample is shown as JSON, a .md sample as prose)."""
from __future__ import annotations

from pathlib import Path


def load_profile(voice_dir: Path, profile: str) -> str:
    root = voice_dir / profile
    if not root.is_dir():
        raise FileNotFoundError(
            f"voice profile '{profile}' not found under {voice_dir} — "
            "author it by dropping samples (see writer-persona.md §bottle)"
        )
    parts = [f"VOICE PROFILE: {profile}"]
    moves = root / "moves.md"
    if moves.exists():
        parts.append(moves.read_text(encoding="utf-8").strip())
    samples = sorted((root / "samples").glob("*")) if (root / "samples").is_dir() else []
    if not samples:
        raise FileNotFoundError(
            f"voice profile '{profile}' has no samples — the exemplars do the "
            "real work; a moves list alone deadens the voice"
        )
    for i, sample in enumerate(samples, 1):
        parts.append(
            f"EXEMPLAR {i} ({sample.name}) — study how it moves:\n"
            + sample.read_text(encoding="utf-8").strip()
        )
    return "\n\n".join(parts)
