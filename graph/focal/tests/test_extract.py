"""focal_extract pipeline tests: seeding, prune, staging, render, explain,
determinism."""

from __future__ import annotations

import pytest

from r2pip_focal.extract import focal_extract
from r2pip_focal.graph import InMemoryKnowledgeGraph


def build_demo_graph() -> InMemoryKnowledgeGraph:
    """Small cross-layer graph: a seed claim, its neighborhood, a far chain,
    a disconnected island, and a staging-tier node."""
    g = InMemoryKnowledgeGraph()
    g.add_node("claim1", type="Claim", layer="research", name="claim one",
               summary="key research claim", embedding=[1.0, 0.0, 0.0],
               confidence=0.9, created_at_days_ago=30)
    g.add_node("need1", type="Need", layer="market", name="need one",
               summary="market need", embedding=[0.9, 0.1, 0.0],
               confidence=0.8, created_at_days_ago=10)
    g.add_node("method1", type="Method", layer="research", name="method one",
               summary="a method", embedding=[0.0, 1.0, 0.0],
               confidence=0.7, created_at_days_ago=200)
    g.add_node("code1", type="CodeBlock", layer="code", name="code one",
               summary="an implementation", confidence=0.95,
               created_at_days_ago=5)
    g.add_node("far1", type="Metric", layer="research", name="far one",
               summary="hop 1", confidence=0.9)
    g.add_node("far2", type="Metric", layer="research", name="far two",
               summary="hop 2", confidence=0.9)
    g.add_node("far3", type="Metric", layer="research", name="far three",
               summary="hop 3", confidence=0.9)
    g.add_node("far4", type="Metric", layer="research", name="far four",
               summary="hop 4 - beyond reach", confidence=0.9)
    g.add_node("island", type="Company", layer="market", name="island co",
               summary="disconnected but shiny", embedding=[1.0, 0.0, 0.0],
               confidence=1.0, created_at_days_ago=0)
    g.add_node("shady", type="MarketSignal", layer="market", name="shady signal",
               summary="unvetted scrape", tier="staging",
               confidence=0.4, created_at_days_ago=1)

    g.add_edge("claim1", "need1", "ADDRESSES", weight=1.0)
    g.add_edge("method1", "claim1", "CITES", weight=0.8)
    g.add_edge("method1", "code1", "IMPLEMENTABLE_AS", weight=1.0)
    g.add_edge("claim1", "far1", "CITES", weight=0.5)
    g.add_edge("far1", "far2", "CITES", weight=0.5)
    g.add_edge("far2", "far3", "CITES", weight=0.5)
    g.add_edge("far3", "far4", "CITES", weight=0.5)
    g.add_edge("shady", "need1", "SIGNALS_DEMAND_FOR", weight=1.0)
    # parallel edges between the same pair (collapse should keep max weight)
    g.add_edge("claim1", "need1", "ADDRESSES", weight=0.4)
    g.add_edge("claim1", "need1", "CITES", weight=0.6)
    return g


# ---------------------------------------------------------------- seeding --


def test_explicit_seed_ids_work():
    fg = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="explain")
    assert fg.seed_ids == ["claim1"]
    assert any(n.id == "claim1" for n in fg.nodes)


def test_embedding_only_seeding_picks_nearest_cosine():
    g = build_demo_graph()
    fg = focal_extract(g, query_embedding=[1.0, 0.0, 0.0], purpose="explain")
    # all embedded trusted nodes are candidates; nearest-cosine ones seed
    assert "claim1" in fg.seed_ids
    assert "island" in fg.seed_ids  # identical embedding to the query
    assert "need1" in fg.seed_ids
    # staging node never seeds by default, embedded or not
    assert "shady" not in fg.seed_ids


def test_both_seeding_inputs_absent_raises():
    with pytest.raises(ValueError):
        focal_extract(build_demo_graph(), purpose="explain")


def test_unresolvable_seed_ids_raise():
    with pytest.raises(ValueError):
        focal_extract(build_demo_graph(), seed_ids=["ghost1", "ghost2"], purpose="explain")


# ------------------------------------------------------------------ prune --


def _hop_distance_to_nearest_seed(g, kept_ids, seeds, node_id):
    from collections import deque

    dist = {node_id: 0}
    q = deque([node_id])
    while q:
        u = q.popleft()
        if u in seeds:
            return dist[u]
        for v, _rel, _w, _d in g.neighbors(u):
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return None


def test_max_nodes_respected_and_over_max_reason_recorded():
    g = build_demo_graph()
    fg = focal_extract(g, seed_ids=["claim1"], purpose="explain", max_nodes=3)
    assert len(fg.nodes) <= 3
    assert "over_max_nodes" in fg.coverage_note


def test_every_kept_non_seed_within_3_hops_of_a_seed():
    g = build_demo_graph()
    fg = focal_extract(g, seed_ids=["claim1"], purpose="explain")
    seeds = set(fg.seed_ids)
    for n in fg.nodes:
        if n.id in seeds:
            continue
        d = _hop_distance_to_nearest_seed(g, {x.id for x in fg.nodes}, seeds, n.id)
        assert d is not None and d <= 3, f"{n.id} is {d} hops from any seed"
    # far4 sits 4 hops out: must not be kept
    assert all(n.id != "far4" for n in fg.nodes)


def test_disconnected_high_score_node_pruned_with_reason():
    """A high-scoring candidate with no trusted path <=3 hops to any seed is
    pruned with reason 'disconnected' in the coverage note.

    'orphan' has perfect confidence/recency (high blended score) and enters
    the PPR frontier through the staging node 'shady' (expansion runs over
    the full graph), but once staging is excluded there is no path to a seed.
    """
    g = build_demo_graph()
    g.add_node("orphan", type="Product", layer="market", name="orphan",
               summary="linked only via staging", confidence=1.0,
               created_at_days_ago=0)
    g.add_edge("shady", "orphan", "COMPETES_WITH", weight=1.0)
    fg = focal_extract(g, seed_ids=["need1"], purpose="explain")
    assert all(n.id != "orphan" for n in fg.nodes)
    assert "disconnected" in fg.coverage_note
    assert "orphan" in fg.coverage_note
    # the never-reached island is simply not a candidate at all
    assert all(n.id != "island" for n in fg.nodes)


def test_node_beyond_three_hops_is_pruned():
    fg = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="explain")
    assert all(n.id != "far4" for n in fg.nodes)  # 4 hops out
    assert any(n.id == "far3" for n in fg.nodes)  # exactly 3 hops: kept


# ---------------------------------------------------------------- staging --


def test_staging_excluded_by_default_with_reason():
    fg = focal_extract(build_demo_graph(), seed_ids=["need1"], purpose="explain")
    assert all(n.id != "shady" for n in fg.nodes)
    assert "staging_tier" in fg.coverage_note
    assert fg.taint == "trusted"


def test_include_staging_flips_taint():
    fg = focal_extract(
        build_demo_graph(), seed_ids=["need1"], purpose="explain", include_staging=True
    )
    assert any(n.id == "shady" and n.tier == "staging" for n in fg.nodes)
    assert fg.taint == "external_untrusted"


# ----------------------------------------------------------------- render --


def test_render_within_token_budget():
    fg = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="explain",
                       token_budget=8000)
    assert len(fg.rendered_context) <= 8000 * 4
    assert "Claim claim1 claim one: key research claim" in fg.rendered_context
    # collapsed parallel edge keeps the max weight (1.0 ADDRESSES)
    assert "claim1 -[ADDRESSES w=1.00]-> need1" in fg.rendered_context
    assert "w=0.40" not in fg.rendered_context


def test_tiny_budget_still_valid_and_notes_trim():
    fg = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="explain",
                       token_budget=15)
    assert len(fg.rendered_context) <= 15 * 4
    assert "trimmed" in fg.coverage_note
    # the FocalGraph object itself is still complete
    assert fg.nodes and fg.seed_ids == ["claim1"]


def test_zero_budget_renders_empty():
    fg = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="explain",
                       token_budget=0)
    assert fg.rendered_context == ""


# ---------------------------------------------------------------- explain --


def test_why_included_nonempty_and_paths_for_non_seeds():
    fg = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="explain")
    seeds = set(fg.seed_ids)
    for n in fg.nodes:
        assert n.why_included
        assert "ppr=" in n.why_included
        if n.id in seeds:
            assert n.why_included.startswith("seed")
        else:
            assert n.why_included.startswith("path: ")
            assert any(s in n.why_included for s in seeds)
            assert "(len" in n.why_included


def test_coverage_note_lists_top_pruned_with_reasons():
    fg = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="explain")
    assert "pruned" in fg.coverage_note
    # far4 (4 hops) and shady (staging) both pruned
    assert "far4" in fg.coverage_note
    assert "shady" in fg.coverage_note


# ------------------------------------------------------------ determinism --


def test_two_identical_calls_identical_focal_graph():
    kwargs = dict(seed_ids=["claim1"], query_embedding=[1.0, 0.0, 0.0],
                  purpose="opportunity_mining", max_nodes=5, token_budget=500)
    a = focal_extract(build_demo_graph(), **kwargs)
    b = focal_extract(build_demo_graph(), **kwargs)
    assert a.model_dump() == b.model_dump()
    assert a.focal_graph_id == b.focal_graph_id


def test_different_inputs_different_id():
    a = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="explain")
    b = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="review")
    assert a.focal_graph_id != b.focal_graph_id


def test_nodes_sorted_by_relevance_then_id():
    fg = focal_extract(build_demo_graph(), seed_ids=["claim1"], purpose="explain")
    keys = [(-n.relevance, n.id) for n in fg.nodes]
    assert keys == sorted(keys)
