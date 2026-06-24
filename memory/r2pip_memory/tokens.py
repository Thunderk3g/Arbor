"""Token estimation — the single source of truth for all budgeting decisions."""

import math


def estimate_tokens(text: str) -> int:
    """Estimate the token count of ``text`` as ceil(len(text) / 4)."""
    return math.ceil(len(text) / 4)
