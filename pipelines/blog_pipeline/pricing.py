"""
Per-model pricing for Anthropic Claude models.

Rates are USD per 1M tokens, separated by input/output. Cache-hit and
cache-write rates are not yet captured — when we wire cache token counts
through the pipeline, extend the dict and compute_cost signature.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("uzelhub_crew")


# Rates supplied by director on 2026-04-26. Update when Anthropic prices change.
MODEL_RATES_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-4-7": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5-20251001": (0.25, 1.25),
}


def compute_cost(
    model: str | None, input_tokens: int, output_tokens: int
) -> float | None:
    """Return USD cost for a single LLM call, or None if model is unknown.

    None signals 'we couldn't price this' so the column stores NULL — distinct
    from 0.0 (priced and free, e.g. a non-LLM step)."""
    if not model:
        return 0.0
    rates = MODEL_RATES_USD_PER_MTOK.get(model)
    if rates is None:
        logger.warning("pricing.unknown_model", extra={"model": model})
        return None
    in_rate, out_rate = rates
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
