"""PPR push algorithm tests: mass conservation, ranking, convergence."""

from __future__ import annotations

import pytest
from focal_helpers import cycle_with_tail, l1_distance, power_iteration_ppr, uniform_weights

from r2pip_focal.ppr import personalized_pagerank


def test_scores_sum_at_most_one_and_terminates_on_cycle():
    g = cycle_with_tail()
    scores = personalized_pagerank(g, {"c0": 1.0}, uniform_weights, epsilon=1e-6)
    assert scores, "expected non-empty score vector"
    assert sum(scores.values()) <= 1.0 + 1e-9
    assert all(v >= 0.0 for v in scores.values())


def test_seed_scores_highest():
    g = cycle_with_tail()
    scores = personalized_pagerank(g, {"c0": 1.0}, uniform_weights, epsilon=1e-7)
    assert max(scores, key=lambda n: scores[n]) == "c0"


def test_mass_decays_along_tail():
    g = cycle_with_tail()
    scores = personalized_pagerank(g, {"c0": 1.0}, uniform_weights, epsilon=1e-7)
    assert scores["t0"] > scores["t1"] > scores.get("t2", 0.0)


def test_smaller_epsilon_converges_to_power_iteration_reference():
    g = cycle_with_tail()
    seeds = {"c0": 1.0}
    reference = power_iteration_ppr(g, seeds, uniform_weights)

    coarse = personalized_pagerank(g, seeds, uniform_weights, epsilon=5e-2)
    fine = personalized_pagerank(g, seeds, uniform_weights, epsilon=1e-8)

    assert l1_distance(fine, reference) <= l1_distance(coarse, reference) + 1e-12
    assert l1_distance(fine, reference) < 1e-4

    # Rank order of the fine approximation matches the reference.
    ref_order = sorted(reference, key=lambda n: (-reference[n], n))
    fine_order = sorted(g.nodes, key=lambda n: (-fine.get(n, 0.0), n))
    assert fine_order == ref_order


def test_edge_weight_fn_biases_the_walk():
    from r2pip_focal.graph import InMemoryKnowledgeGraph

    g = InMemoryKnowledgeGraph()
    for nid in ("seed", "hot", "cold"):
        g.add_node(nid, type="Claim", layer="research", name=nid)
    g.add_edge("seed", "hot", "SIGNALS_DEMAND_FOR")
    g.add_edge("seed", "cold", "CITES")

    def fn(rel: str) -> float:
        return 5.0 if rel == "SIGNALS_DEMAND_FOR" else 1.0

    scores = personalized_pagerank(g, {"seed": 1.0}, fn, epsilon=1e-7)
    assert scores["hot"] > scores["cold"]


def test_empty_seeds_rejected():
    g = cycle_with_tail()
    with pytest.raises(ValueError):
        personalized_pagerank(g, {}, uniform_weights)


def test_unknown_seed_rejected():
    g = cycle_with_tail()
    with pytest.raises(KeyError):
        personalized_pagerank(g, {"nope": 1.0}, uniform_weights)
