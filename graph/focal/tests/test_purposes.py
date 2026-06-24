"""Purpose profiles and purpose-conditioned ranking."""

from __future__ import annotations

import pytest

from r2pip_focal.extract import focal_extract
from r2pip_focal.graph import InMemoryKnowledgeGraph
from r2pip_focal.purposes import PURPOSE_PROFILES, coefficients_for, edge_weight_fn_for

ALL_PURPOSES = ["opportunity_mining", "code_task_brief", "spec_drafting", "review", "explain"]


def test_all_five_purposes_present_with_coefficients():
    assert sorted(PURPOSE_PROFILES) == sorted(ALL_PURPOSES)
    for purpose in ALL_PURPOSES:
        coeffs = coefficients_for(purpose)
        assert set(coeffs) == {"alpha_ppr", "beta_semantic", "gamma_confidence", "delta_recency"}
        assert all(v >= 0 for v in coeffs.values())


def test_specified_edge_weights():
    om = edge_weight_fn_for("opportunity_mining")
    assert om("CONTRADICTS") == 2.0
    assert om("SIGNALS_DEMAND_FOR") == 2.5
    assert om("ADDRESSES") == 2.0
    assert om("SOMETHING_ELSE") == 1.0

    ctb = edge_weight_fn_for("code_task_brief")
    assert ctb("DEPENDS_ON") == 2.5
    assert ctb("IMPLEMENTS") == 2.5
    assert ctb("IMPLEMENTABLE_AS") == 2.0
    assert ctb("SOMETHING_ELSE") == 1.0


def test_unknown_purpose_raises():
    with pytest.raises(ValueError):
        edge_weight_fn_for("world_domination")


def _purpose_graph() -> InMemoryKnowledgeGraph:
    """Seed S; A reachable via SIGNALS_DEMAND_FOR, B via DEPENDS_ON.

    Equal distance (1 hop), equal stored weights, identical node attributes —
    only the purpose's edge-type multipliers can break the tie.
    """
    g = InMemoryKnowledgeGraph()
    g.add_node("S", type="Method", layer="research", name="seed method")
    g.add_node("A", type="MarketSignal", layer="market", name="demand signal")
    g.add_node("B", type="Dependency", layer="code", name="library dep")
    g.add_edge("S", "A", "SIGNALS_DEMAND_FOR", weight=1.0)
    g.add_edge("S", "B", "DEPENDS_ON", weight=1.0)
    return g


def _relevance_map(fg):
    return {n.id: n.relevance for n in fg.nodes}


def test_opportunity_mining_ranks_demand_signal_above_dependency():
    fg = focal_extract(_purpose_graph(), seed_ids=["S"], purpose="opportunity_mining")
    rel = _relevance_map(fg)
    assert rel["A"] > rel["B"]


def test_code_task_brief_ranks_dependency_above_demand_signal():
    fg = focal_extract(_purpose_graph(), seed_ids=["S"], purpose="code_task_brief")
    rel = _relevance_map(fg)
    assert rel["B"] > rel["A"]
