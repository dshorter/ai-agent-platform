"""The SEO doctrine loader — convention-path loader, twin of the voice bottle.

    config/seo/<sink>.md   — the operational SEO rules for one publishing sink.

Doctrine is loaded at runtime and assembled into a prompt block, exactly the way
`pipelines/writer/bottle.py` loads a voice profile. It is deliberately NOT a
string constant in an agent module: the Marketer's hardcoded prompt carried a
wrong hostname and a stale indexing claim for roughly three months because
nothing could notice the drift (survey 2026-08-13).

A new sink is authored by dropping `config/seo/<sink>.md` — no code change.

The human source of truth is `/opt/_host/SEO.md`, which is local to the box and
outside this (public) repo. These extracts carry operational rules only; keep
strategy out of them.
"""
from __future__ import annotations

from pathlib import Path

# repo root — agents/ sits one level below it
DOCTRINE_DIR = Path(__file__).resolve().parents[1] / "config" / "seo"


def load_doctrine(sink: str, doctrine_dir: Path | None = None) -> str:
    """Return the doctrine block for `sink`, ready to append to a system prompt.

    Raises FileNotFoundError if the sink has no doctrine. That is deliberate:
    packaging a post against no rules at all is the failure this loader exists
    to prevent, and it should stop the run rather than quietly proceed — the
    same posture bottle.py takes on a missing voice profile.
    """
    root = doctrine_dir or DOCTRINE_DIR
    path = root / f"{sink}.md"
    if not path.is_file():
        raise FileNotFoundError(
            f"no SEO doctrine for sink '{sink}' at {path} — author it by "
            f"dropping the file (see /opt/_host/SEO.md for the source of truth)"
        )
    body = path.read_text(encoding="utf-8").strip()
    if not body:
        raise FileNotFoundError(f"SEO doctrine for sink '{sink}' is empty: {path}")
    return body
