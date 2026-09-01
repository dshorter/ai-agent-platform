"""
Per-model pricing for Anthropic Claude models.

Rates are USD per 1M tokens, separated by input/output. Cache pricing follows
Anthropic's standard multipliers off the base input rate:
  - cache write: 1.25x base input rate
  - cache read:  0.10x base input rate
The Anthropic API reports input_tokens, cache_creation_input_tokens, and
cache_read_input_tokens as three disjoint counts in the usage object.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("uzelhub_crew")


CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.10


# Rates supplied by Blog Director on 2026-04-26. Update when Anthropic prices change.
MODEL_RATES_USD_PER_MTOK: dict[str, tuple[float, float]] = {
    # Sonnet 5 (launched 2026-06-30) shipped at an "introductory" $2/$10 per MTok with a
    # rise to $3/$15 announced for 2026-09-01. Anthropic made the promotional rate
    # permanent instead (operator, 2026-09-01; the Sept-1 predictor boundary script was
    # stood down 2026-08-30 on the same grounds). $2/$10 IS the standard rate — do not
    # "restore" $3/$15 here, whatever an older reminder says.
    "claude-sonnet-5": (2.00, 10.00),
    "claude-fable-5": (10.00, 50.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    # Corrected 2026-08-29: was (0.25, 1.25), which is Haiku 3.5's old rate.
    # Haiku 4.5 is $1/$5. The understatement flowed into every Scout walk
    # figure in scout-mining-economics.md -- a corpus re-walk is ~$4, not ~$1.
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}


def compute_cost(
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    cache_create_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> float | None:
    """Return USD cost for a single LLM call, or None if model is unknown.

    None signals 'we couldn't price this' so the column stores NULL — distinct
    from 0.0 (priced and free, e.g. a non-LLM step).

    The Anthropic usage object returns input_tokens, cache_creation_input_tokens,
    and cache_read_input_tokens as three disjoint counts (the cached ones are
    NOT a subset of input_tokens). We bill all three separately."""
    if not model:
        return 0.0
    rates = MODEL_RATES_USD_PER_MTOK.get(model)
    if rates is None:
        logger.warning("pricing.unknown_model", extra={"model": model})
        return None
    in_rate, out_rate = rates
    cost = (
        input_tokens * in_rate
        + cache_create_tokens * in_rate * CACHE_WRITE_MULTIPLIER
        + cache_read_tokens * in_rate * CACHE_READ_MULTIPLIER
        + output_tokens * out_rate
    ) / 1_000_000
    return cost
