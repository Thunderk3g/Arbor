"""r2pip_focal — Focal Graph engine prototype (RFC-001 §4.4, ADR-007).

Self-contained, in-memory implementation of the SEED / EXPAND / SCORE /
PRUNE / EXPLAIN / RENDER pipeline behind the ``focal.extract`` tool.
No Neo4j, no Milvus — pure Python + pydantic v2.
"""

from r2pip_focal.extract import FocalEdge, FocalGraph, FocalNode, focal_extract
from r2pip_focal.graph import InMemoryKnowledgeGraph
from r2pip_focal.ppr import personalized_pagerank
from r2pip_focal.purposes import (
    PURPOSE_PROFILES,
    coefficients_for,
    edge_weight_fn_for,
)

__all__ = [
    "FocalEdge",
    "FocalGraph",
    "FocalNode",
    "InMemoryKnowledgeGraph",
    "PURPOSE_PROFILES",
    "coefficients_for",
    "edge_weight_fn_for",
    "focal_extract",
    "personalized_pagerank",
]
