"""In-memory typed knowledge graph for the Focal Graph prototype.

Directed multigraph with O(1) node and adjacency lookups. The graph stores
reverse adjacency as well, because Focal Graph expansion (PPR) treats every
edge as traversable in both directions — a ``Claim -ADDRESSES-> Need`` edge
is just as useful when walking from the Need back to the Claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Optional


@dataclass
class Node:
    """A typed entity node (ENTITY_NODE in the RFC §4.3 ER diagram)."""

    id: str
    type: str
    layer: str
    name: str
    summary: str = ""
    confidence: float = 1.0
    tier: str = "trusted"  # "staging" | "trusted" (§4.5 trust tiers)
    embedding: Optional[list[float]] = None
    created_at_days_ago: float = 0.0


@dataclass
class Edge:
    """A typed, weighted, directed relation (RELATION_EDGE)."""

    source: str
    target: str
    relationship: str
    weight: float = 1.0


@dataclass
class InMemoryKnowledgeGraph:
    """Directed knowledge graph with both-ways adjacency for expansion."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    # adjacency: node_id -> list of (other_id, relationship, weight)
    _out: dict[str, list[tuple[str, str, float]]] = field(default_factory=dict)
    _in: dict[str, list[tuple[str, str, float]]] = field(default_factory=dict)

    def add_node(
        self,
        id: str,
        type: str,
        layer: str,
        name: str,
        summary: str = "",
        confidence: float = 1.0,
        tier: str = "trusted",
        embedding: Optional[list[float]] = None,
        created_at_days_ago: float = 0.0,
    ) -> Node:
        node = Node(
            id=id,
            type=type,
            layer=layer,
            name=name,
            summary=summary,
            confidence=confidence,
            tier=tier,
            embedding=list(embedding) if embedding is not None else None,
            created_at_days_ago=created_at_days_ago,
        )
        self.nodes[id] = node
        self._out.setdefault(id, [])
        self._in.setdefault(id, [])
        return node

    def add_edge(
        self, source: str, target: str, relationship: str, weight: float = 1.0
    ) -> Edge:
        if source not in self.nodes:
            raise KeyError(f"unknown source node: {source!r}")
        if target not in self.nodes:
            raise KeyError(f"unknown target node: {target!r}")
        edge = Edge(source=source, target=target, relationship=relationship, weight=weight)
        self.edges.append(edge)
        self._out[source].append((target, relationship, weight))
        self._in[target].append((source, relationship, weight))
        return edge

    def has_node(self, id: str) -> bool:
        return id in self.nodes

    def neighbors(self, id: str) -> Iterator[tuple[str, str, float, str]]:
        """Yield (neighbor_id, relationship, weight, direction).

        ``direction`` is "out" when the stored edge points *from* ``id`` and
        "in" when it points *to* ``id``. Both are yielded because traversal
        is bidirectional.
        """
        for target, rel, weight in self._out.get(id, ()):
            yield (target, rel, weight, "out")
        for source, rel, weight in self._in.get(id, ()):
            yield (source, rel, weight, "in")
