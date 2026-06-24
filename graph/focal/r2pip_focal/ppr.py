"""Approximate Personalized PageRank via the push algorithm.

Andersen–Chung–Lang style local push (FOCS'06, "Local Graph Partitioning
using PageRank Vectors"), adapted to typed weighted edges:

* Maintain an *estimate* vector ``p`` and a *residual* vector ``r``;
  initially all probability mass sits in ``r`` on the seed nodes.
* While any node ``u`` has residual ``r[u] > epsilon * degree(u)``:
  push: move ``alpha * r[u]`` into ``p[u]`` and spread the remaining
  ``(1 - alpha) * r[u]`` over u's neighbors proportionally to the
  purpose-conditioned edge weight ``edge_weight(rel) * weight``.
* Dangling nodes (zero effective degree) absorb their residual into ``p``.

Invariant: ``sum(p) + sum(r) == 1`` throughout, so returned scores always
sum to <= 1 and the algorithm terminates even on cyclic graphs — every push
permanently moves at least ``alpha * epsilon * degree(u)`` of mass out of
the residual, and total mass is bounded.

Complexity: the number of pushes is O(1 / (alpha * epsilon)) — i.e.
**independent of graph size** — because each push retires at least an
``alpha * epsilon`` fraction of (degree-normalized) residual mass and the
total degree-normalized residual starts at sum_s seeds[s]/deg(s) <= 1/eps
budget. This is exactly why ADR-007 picks PPR-push: Focal Graph extraction
stays interactive at TB scale (§4.6).

Edges are traversed in BOTH directions (the graph yields reverse adjacency
from ``neighbors``), matching Focal Graph expansion semantics.
"""

from __future__ import annotations

from collections import deque
from typing import Callable

from r2pip_focal.graph import InMemoryKnowledgeGraph


def personalized_pagerank(
    graph: InMemoryKnowledgeGraph,
    seeds: dict[str, float],
    edge_weight_fn: Callable[[str], float],
    alpha: float = 0.15,
    epsilon: float = 1e-4,
) -> dict[str, float]:
    """Approximate PPR scores for a seed distribution.

    Args:
        graph: the knowledge graph (bidirectional traversal).
        seeds: node_id -> teleport mass (normalized internally; must be > 0
            in total and every seed must exist in the graph).
        edge_weight_fn: relationship -> multiplier applied on top of the
            stored edge weight (purpose conditioning). Multipliers <= 0
            make an edge non-traversable.
        alpha: teleport (restart) probability.
        epsilon: push tolerance; smaller -> closer to exact PPR.

    Returns:
        dict node_id -> approximate PPR score; scores sum to <= 1.
    """
    if not seeds:
        raise ValueError("personalized_pagerank requires a non-empty seed set")
    for s in seeds:
        if not graph.has_node(s):
            raise KeyError(f"seed node not in graph: {s!r}")
    total = float(sum(seeds.values()))
    if total <= 0.0:
        raise ValueError("seed masses must sum to a positive value")

    # Effective (purpose-conditioned) weighted degree, cached per call.
    degree_cache: dict[str, float] = {}

    def degree(u: str) -> float:
        d = degree_cache.get(u)
        if d is None:
            d = 0.0
            for _, rel, w, _ in graph.neighbors(u):
                m = edge_weight_fn(rel) * w
                if m > 0.0:
                    d += m
            degree_cache[u] = d
        return d

    p: dict[str, float] = {}
    r: dict[str, float] = {nid: mass / total for nid, mass in sorted(seeds.items())}

    queue: deque[str] = deque(sorted(r))  # deterministic processing order
    in_queue: set[str] = set(queue)

    while queue:
        u = queue.popleft()
        in_queue.discard(u)
        ru = r.get(u, 0.0)
        if ru <= 0.0:
            continue
        du = degree(u)
        if du <= 0.0:
            # Dangling node: nowhere to walk; absorb the residual so the
            # p + r = 1 invariant (and termination) holds.
            p[u] = p.get(u, 0.0) + ru
            r[u] = 0.0
            continue
        if ru <= epsilon * du:
            continue

        p[u] = p.get(u, 0.0) + alpha * ru
        share = (1.0 - alpha) * ru / du
        r[u] = 0.0
        for v, rel, w, _ in graph.neighbors(u):
            m = edge_weight_fn(rel) * w
            if m <= 0.0:
                continue
            rv = r.get(v, 0.0) + share * m
            r[v] = rv
            if v not in in_queue and rv > epsilon * degree(v):
                queue.append(v)
                in_queue.add(v)

    return p
