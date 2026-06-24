"""focal_extract — the 6-step Focal Graph pipeline (RFC §4.4, ADR-007).

SEED    -> resolve caller seeds ∪ cosine top-k over node embeddings
EXPAND  -> personalized PageRank (push) with purpose-conditioned edge weights
SCORE   -> relevance = a*ppr_norm + b*semantic + g*confidence + d*recency
PRUNE   -> greedy keep-if-connected-to-seed-within-3-hops, max_nodes cap,
           parallel-edge collapse, staging-tier exclusion (taint defense §4.5)
EXPLAIN -> per-node why_included (shortest path to nearest seed + factors),
           coverage_note (top pruned candidates + reasons + render trims)
RENDER  -> typed adjacency text trimmed to token_budget (1 token ~ 4 chars)
"""

from __future__ import annotations

import hashlib
import json
import math
import uuid
from collections import deque
from typing import Optional, Sequence

from pydantic import BaseModel, Field

from r2pip_focal.graph import InMemoryKnowledgeGraph
from r2pip_focal.ppr import personalized_pagerank
from r2pip_focal.purposes import coefficients_for, edge_weight_fn_for

_EMBED_SEED_TOP_K = 8
_MAX_HOPS_TO_SEED = 3
_CHARS_PER_TOKEN = 4
_COVERAGE_TOP_N = 5


# --------------------------------------------------------------------------
# Output model (mirrors the focal.extract outputSchema, RFC §3.2)
# --------------------------------------------------------------------------


class FocalNode(BaseModel):
    id: str
    type: str
    layer: str
    summary: str = ""
    relevance: float
    why_included: str
    tier: str = "trusted"


class FocalEdge(BaseModel):
    source: str
    target: str
    relationship: str
    weight: float = 1.0


class FocalGraph(BaseModel):
    focal_graph_id: str
    purpose: str
    nodes: list[FocalNode] = Field(default_factory=list)
    edges: list[FocalEdge] = Field(default_factory=list)
    rendered_context: str = ""
    coverage_note: str = ""
    seed_ids: list[str] = Field(default_factory=list)
    # Trust taint propagated to the prompt assembler / tool firewall (§7.6):
    # including staging-tier nodes downgrades the whole brief.
    taint: str = "trusted"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _cosine(a: Optional[Sequence[float]], b: Optional[Sequence[float]]) -> float:
    """Cosine similarity; 0.0 when either vector is missing/empty/mismatched."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / math.sqrt(na * nb)


def _recency(days_ago: float) -> float:
    """exp(-age/365): 1.0 today, ~0.37 after a year (confidence-decay kin)."""
    return math.exp(-max(days_ago, 0.0) / 365.0)


def _deterministic_id(payload: dict) -> str:
    """UUID-shaped id derived from sha256 of the call inputs (determinism)."""
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).digest()
    return str(uuid.UUID(bytes=digest[:16]))


def _graph_fingerprint(graph: InMemoryKnowledgeGraph) -> str:
    h = hashlib.sha256()
    for nid in sorted(graph.nodes):
        n = graph.nodes[nid]
        h.update(
            repr(
                (n.id, n.type, n.layer, n.name, n.summary, n.confidence, n.tier,
                 n.embedding, n.created_at_days_ago)
            ).encode("utf-8")
        )
    for e in sorted(graph.edges, key=lambda e: (e.source, e.target, e.relationship, e.weight)):
        h.update(repr((e.source, e.target, e.relationship, e.weight)).encode("utf-8"))
    return h.hexdigest()


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------


def focal_extract(
    graph: InMemoryKnowledgeGraph,
    *,
    query_embedding: Optional[Sequence[float]] = None,
    seed_ids: Optional[Sequence[str]] = None,
    purpose: str = "explain",
    max_nodes: int = 150,
    token_budget: int = 8000,
    include_staging: bool = False,
) -> FocalGraph:
    """Build a Focal Graph: minimal, ranked, explained subgraph for one task."""
    if max_nodes < 1:
        raise ValueError("max_nodes must be >= 1")
    if token_budget < 0:
        raise ValueError("token_budget must be >= 0")

    edge_weight_fn = edge_weight_fn_for(purpose)
    coeffs = coefficients_for(purpose)

    def allowed(nid: str) -> bool:
        return include_staging or graph.nodes[nid].tier != "staging"

    # ---- 1. SEED ----------------------------------------------------------
    if seed_ids is None and query_embedding is None:
        raise ValueError("focal_extract requires seed_ids and/or query_embedding")

    seeds: list[str] = []
    seen: set[str] = set()
    if seed_ids:
        for sid in seed_ids:
            if sid in graph.nodes and allowed(sid) and sid not in seen:
                seeds.append(sid)
                seen.add(sid)
    if query_embedding is not None:
        scored = []
        for nid in sorted(graph.nodes):
            node = graph.nodes[nid]
            if node.embedding is None or not allowed(nid):
                continue
            sim = _cosine(query_embedding, node.embedding)
            scored.append((-sim, nid))
        scored.sort()
        for neg_sim, nid in scored[:_EMBED_SEED_TOP_K]:
            if nid not in seen:
                seeds.append(nid)
                seen.add(nid)
    if not seeds:
        raise ValueError("no seeds resolved (unknown ids / no embedded nodes)")
    seeds = sorted(seeds)
    seed_set = set(seeds)

    # ---- 2. EXPAND (PPR push from uniform seed distribution) --------------
    ppr = personalized_pagerank(
        graph,
        {s: 1.0 / len(seeds) for s in seeds},
        edge_weight_fn,
    )
    for s in seeds:  # isolated seeds may get no push mass; keep them anyway
        ppr.setdefault(s, 0.0)

    frontier_cap = max_nodes * 4
    candidates = sorted(ppr, key=lambda n: (-ppr[n], n))
    candidates = sorted(set(candidates[:frontier_cap]) | seed_set,
                        key=lambda n: (-ppr[n], n))

    # pruned: node_id -> (reason, sort_score)
    pruned: dict[str, tuple[str, float]] = {}

    # Staging-tier exclusion (poisoning defense, §4.5).
    visible: list[str] = []
    for nid in candidates:
        if allowed(nid):
            visible.append(nid)
        else:
            pruned[nid] = ("staging_tier", ppr[nid])
    candidates = visible

    # ---- 3. SCORE ----------------------------------------------------------
    max_ppr = max((ppr[n] for n in candidates), default=0.0)
    relevance: dict[str, float] = {}
    factors: dict[str, dict[str, float]] = {}
    for nid in candidates:
        node = graph.nodes[nid]
        ppr_norm = (ppr[nid] / max_ppr) if max_ppr > 0 else 0.0
        sem = _cosine(query_embedding, node.embedding)
        conf = node.confidence
        rec = _recency(node.created_at_days_ago)
        relevance[nid] = (
            coeffs["alpha_ppr"] * ppr_norm
            + coeffs["beta_semantic"] * sem
            + coeffs["gamma_confidence"] * conf
            + coeffs["delta_recency"] * rec
        )
        factors[nid] = {"ppr": ppr_norm, "sem": sem, "conf": conf, "rec": rec}

    by_score = sorted(candidates, key=lambda n: (-relevance[n], n))

    # ---- 4. PRUNE ----------------------------------------------------------
    # Multi-source BFS from the seeds over visible nodes: distance + parent
    # tree gives both the <=3-hop connectivity test and the EXPLAIN paths.
    dist: dict[str, int] = {s: 0 for s in seeds}
    # parent[nid] = (parent_id, relationship, direction-of-stored-edge)
    parent: dict[str, tuple[str, str, str]] = {}
    bfs_q: deque[str] = deque(seeds)
    while bfs_q:
        u = bfs_q.popleft()
        for v, rel, w, direction in sorted(graph.neighbors(u)):
            if v in dist or not allowed(v):
                continue
            dist[v] = dist[u] + 1
            parent[v] = (u, rel, direction)
            bfs_q.append(v)

    kept: list[str] = []
    kept_set: set[str] = set()
    # Seeds first (a focal graph without its anchors is unexplainable).
    for nid in sorted(seed_set, key=lambda n: (-relevance.get(n, 0.0), n)):
        if len(kept) >= max_nodes:
            pruned[nid] = ("over_max_nodes", relevance.get(nid, 0.0))
            continue
        kept.append(nid)
        kept_set.add(nid)
    # Then greedy by blended score: keep iff within 3 hops of a seed.
    for nid in by_score:
        if nid in kept_set or nid in pruned:
            continue
        if nid not in dist or dist[nid] > _MAX_HOPS_TO_SEED:
            pruned[nid] = ("disconnected", relevance[nid])
            continue
        if len(kept) >= max_nodes:
            pruned[nid] = ("over_max_nodes", relevance[nid])
            continue
        kept.append(nid)
        kept_set.add(nid)

    kept.sort(key=lambda n: (-relevance.get(n, 0.0), n))

    # Collapse parallel edges between kept pairs: keep the max-weight edge
    # per directed (source, target) pair; ties broken by relationship name.
    best_edge: dict[tuple[str, str], tuple[float, str]] = {}
    for e in graph.edges:
        if e.source in kept_set and e.target in kept_set:
            key = (e.source, e.target)
            cand = (e.weight, e.relationship)
            cur = best_edge.get(key)
            if cur is None or cand[0] > cur[0] or (cand[0] == cur[0] and cand[1] < cur[1]):
                best_edge[key] = cand
    edges = [
        FocalEdge(source=s, target=t, relationship=rel, weight=w)
        for (s, t), (w, rel) in sorted(
            best_edge.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[1][1])
        )
    ]

    # ---- 5. EXPLAIN --------------------------------------------------------
    def path_string(nid: str) -> str:
        """Render the BFS shortest path from the nearest seed down to nid."""
        hops: list[tuple[str, str, str]] = []  # (rel, direction, child)
        cur = nid
        while cur not in seed_set:
            par, rel, direction = parent[cur]
            hops.append((rel, direction, cur))
            cur = par
        parts = [cur]  # the seed
        for rel, direction, child in reversed(hops):
            arrow = f"-[{rel}]->" if direction == "out" else f"<-[{rel}]-"
            parts.append(arrow)
            parts.append(child)
        return "".join(parts) + f" (len {len(hops)})"

    nodes_out: list[FocalNode] = []
    for nid in kept:
        node = graph.nodes[nid]
        f = factors.get(nid, {"ppr": 0.0, "sem": 0.0, "conf": node.confidence,
                              "rec": _recency(node.created_at_days_ago)})
        factor_str = (
            f"ppr={f['ppr']:.3f}, sem={f['sem']:.3f}, "
            f"conf={f['conf']:.2f}, rec={f['rec']:.2f}"
        )
        if nid in seed_set:
            why = f"seed; {factor_str}"
        else:
            why = f"path: {path_string(nid)}; {factor_str}"
        nodes_out.append(
            FocalNode(
                id=nid,
                type=node.type,
                layer=node.layer,
                summary=node.summary,
                relevance=round(relevance.get(nid, 0.0), 6),
                why_included=why,
                tier=node.tier,
            )
        )

    coverage_parts: list[str] = []
    if pruned:
        top_pruned = sorted(pruned.items(), key=lambda kv: (-kv[1][1], kv[0]))
        listed = "; ".join(
            f"{nid} ({reason}, score={score:.3f})"
            for nid, (reason, score) in top_pruned[:_COVERAGE_TOP_N]
        )
        coverage_parts.append(
            f"pruned {len(pruned)} candidate(s); top by score: {listed}"
        )
    else:
        coverage_parts.append("no candidates pruned")

    # ---- 6. RENDER ---------------------------------------------------------
    char_budget = token_budget * _CHARS_PER_TOKEN

    def render(render_ids: set[str]) -> str:
        lines: list[str] = []
        for fn in nodes_out:
            if fn.id in render_ids:
                name = graph.nodes[fn.id].name
                lines.append(f"{fn.type} {fn.id} {name}: {fn.summary}")
        for fe in edges:
            if fe.source in render_ids and fe.target in render_ids:
                lines.append(
                    f"{fe.source} -[{fe.relationship} w={fe.weight:.2f}]-> {fe.target}"
                )
        return "\n".join(lines)

    render_ids = set(kept)
    rendered = render(render_ids)
    trimmed = 0
    # Drop lowest-relevance nodes' lines (node line + incident edge lines)
    # until the serialization fits the token budget.
    drop_order = list(reversed(kept))  # kept is sorted best-first
    while len(rendered) > char_budget and render_ids:
        render_ids.discard(drop_order[trimmed])
        trimmed += 1
        rendered = render(render_ids)
    if trimmed:
        coverage_parts.append(
            f"rendered_context trimmed: dropped lines for {trimmed} "
            f"lowest-relevance node(s) to fit token_budget={token_budget}"
        )

    coverage_note = ". ".join(coverage_parts) + "."

    focal_graph_id = _deterministic_id(
        {
            "graph": _graph_fingerprint(graph),
            "query_embedding": list(query_embedding) if query_embedding is not None else None,
            "seed_ids": list(seed_ids) if seed_ids is not None else None,
            "purpose": purpose,
            "max_nodes": max_nodes,
            "token_budget": token_budget,
            "include_staging": include_staging,
        }
    )

    # Conservative taint rule (§4.5/§7.6): merely *requesting* staging
    # inclusion downgrades the brief, whether or not staging nodes made it in.
    taint = "external_untrusted" if include_staging else "trusted"

    return FocalGraph(
        focal_graph_id=focal_graph_id,
        purpose=purpose,
        nodes=nodes_out,
        edges=edges,
        rendered_context=rendered,
        coverage_note=coverage_note,
        seed_ids=seeds,
        taint=taint,
    )
