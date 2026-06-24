"""Purpose conditioning profiles for Focal Graph extraction (RFC §4.4 step 2/3).

Each purpose (the ``focal.extract`` tool enum: opportunity_mining,
spec_drafting, code_task_brief, review, explain) carries:

* ``edge_weights`` — relationship-type multipliers applied during PPR
  expansion (anything not listed gets ``default_edge_weight``), and
* ``coefficients`` — the (alpha_ppr, beta_semantic, gamma_confidence,
  delta_recency) blend used in the SCORE step:

      relevance(n) = alpha_ppr * PPR_norm(n)
                   + beta_semantic * cos(emb(n), emb(query))
                   + gamma_confidence * confidence(n)
                   + delta_recency * recency(n)

A learned-to-rank model replaces the linear blend post-Alpha (OQ-1).
"""

from __future__ import annotations

from typing import Callable

PURPOSE_PROFILES: dict[str, dict] = {
    # Hunting for arbitrage: contradictions in the literature and market
    # demand signals are the gold; recency matters (markets move).
    "opportunity_mining": {
        "edge_weights": {
            "CONTRADICTS": 2.0,
            "SIGNALS_DEMAND_FOR": 2.5,
            "ADDRESSES": 2.0,
        },
        "default_edge_weight": 1.0,
        "coefficients": {
            "alpha_ppr": 0.50,
            "beta_semantic": 0.20,
            "gamma_confidence": 0.15,
            "delta_recency": 0.15,
        },
    },
    # Briefing a coding agent: structural code relations dominate; recency
    # barely matters (the dependency graph is the dependency graph).
    "code_task_brief": {
        "edge_weights": {
            "DEPENDS_ON": 2.5,
            "IMPLEMENTS": 2.5,
            "IMPLEMENTABLE_AS": 2.0,
        },
        "default_edge_weight": 1.0,
        "coefficients": {
            "alpha_ppr": 0.55,
            "beta_semantic": 0.25,
            "gamma_confidence": 0.15,
            "delta_recency": 0.05,
        },
    },
    # Drafting a spec: cross-layer "what addresses what / what is
    # implementable as what" edges plus semantic closeness to the ask.
    "spec_drafting": {
        "edge_weights": {
            "ADDRESSES": 1.75,
            "IMPLEMENTABLE_AS": 1.75,
            "DEPENDS_ON": 1.25,
            "SIGNALS_DEMAND_FOR": 1.25,
        },
        "default_edge_weight": 1.0,
        "coefficients": {
            "alpha_ppr": 0.45,
            "beta_semantic": 0.30,
            "gamma_confidence": 0.15,
            "delta_recency": 0.10,
        },
    },
    # Reviewing claims: provenance confidence is weighted up, and edges
    # that surface counter-evidence are favored.
    "review": {
        "edge_weights": {
            "CONTRADICTS": 1.75,
            "EVALUATED_ON": 1.5,
            "CITES": 1.25,
        },
        "default_edge_weight": 1.0,
        "coefficients": {
            "alpha_ppr": 0.40,
            "beta_semantic": 0.20,
            "gamma_confidence": 0.30,
            "delta_recency": 0.10,
        },
    },
    # Neutral explanation: no relationship bias, balanced blend.
    "explain": {
        "edge_weights": {},
        "default_edge_weight": 1.0,
        "coefficients": {
            "alpha_ppr": 0.50,
            "beta_semantic": 0.25,
            "gamma_confidence": 0.15,
            "delta_recency": 0.10,
        },
    },
}


def _profile(purpose: str) -> dict:
    try:
        return PURPOSE_PROFILES[purpose]
    except KeyError:
        raise ValueError(
            f"unknown purpose {purpose!r}; expected one of {sorted(PURPOSE_PROFILES)}"
        ) from None


def edge_weight_fn_for(purpose: str) -> Callable[[str], float]:
    """Return relationship -> multiplier function for a purpose."""
    profile = _profile(purpose)
    weights: dict[str, float] = profile["edge_weights"]
    default: float = profile["default_edge_weight"]

    def edge_weight(relationship: str) -> float:
        return weights.get(relationship, default)

    return edge_weight


def coefficients_for(purpose: str) -> dict[str, float]:
    """Return the SCORE-step coefficient set for a purpose."""
    return dict(_profile(purpose)["coefficients"])
