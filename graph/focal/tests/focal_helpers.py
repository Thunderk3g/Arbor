"""Shared helpers for the Focal Graph test suite (not a conftest)."""

from __future__ import annotations

from typing import Callable

from r2pip_focal.graph import InMemoryKnowledgeGraph


def uniform_weights(_relationship: str) -> float:
    return 1.0


def cycle_with_tail() -> InMemoryKnowledgeGraph:
    """Directed cycle c0->c1->c2->c3->c0 plus tail c0->t0->t1->t2."""
    g = InMemoryKnowledgeGraph()
    for i in range(4):
        g.add_node(f"c{i}", type="Method", layer="research", name=f"cycle {i}")
    for i in range(3):
        g.add_node(f"t{i}", type="Method", layer="research", name=f"tail {i}")
    for i in range(4):
        g.add_edge(f"c{i}", f"c{(i + 1) % 4}", "CITES")
    g.add_edge("c0", "t0", "CITES")
    g.add_edge("t0", "t1", "CITES")
    g.add_edge("t1", "t2", "CITES")
    return g


def power_iteration_ppr(
    graph: InMemoryKnowledgeGraph,
    seeds: dict[str, float],
    edge_weight_fn: Callable[[str], float],
    alpha: float = 0.15,
    iterations: int = 500,
) -> dict[str, float]:
    """Dense power-iteration reference for PPR (same bidirectional walk)."""
    total = sum(seeds.values())
    s = {nid: seeds.get(nid, 0.0) / total for nid in graph.nodes}

    def degree(u: str) -> float:
        return sum(
            edge_weight_fn(rel) * w
            for _, rel, w, _ in graph.neighbors(u)
            if edge_weight_fn(rel) * w > 0
        )

    pi = dict(s)
    for _ in range(iterations):
        nxt = {nid: alpha * s[nid] for nid in graph.nodes}
        for u in graph.nodes:
            mass = (1.0 - alpha) * pi[u]
            du = degree(u)
            if du <= 0:
                nxt[u] += mass  # dangling: stay put
                continue
            for v, rel, w, _ in graph.neighbors(u):
                m = edge_weight_fn(rel) * w
                if m > 0:
                    nxt[v] += mass * m / du
        pi = nxt
    return pi


def l1_distance(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys)
