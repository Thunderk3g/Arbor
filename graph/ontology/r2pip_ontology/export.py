"""Export a loaded ontology as Neo4j DDL and as JSON Schema for graph.write."""

from __future__ import annotations

from typing import Dict, List

from .models import Ontology

_PROVENANCE_SCHEMA: Dict[str, object] = {
    "type": "object",
    "required": ["source_type", "source_ref", "extractor", "confidence"],
    "properties": {
        "source_type": {
            "enum": ["paper", "market_feed", "telemetry", "agent_inference", "human"]
        },
        "source_ref": {"type": "string"},
        "extractor": {
            "type": "string",
            "description": "model id + prompt version",
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "taint": {
            "enum": ["trusted", "external_untrusted"],
            "default": "external_untrusted",
        },
    },
}


def to_cypher(ontology: Ontology) -> List[str]:
    """One id-uniqueness constraint and one (tenant_id, canonical_name) index per node type."""
    statements: List[str] = []
    for nt in ontology.node_types:
        ident = nt.name.lower()
        statements.append(
            f"CREATE CONSTRAINT {ident}_id_unique IF NOT EXISTS "
            f"FOR (n:{nt.name}) REQUIRE n.id IS UNIQUE"
        )
        statements.append(
            f"CREATE INDEX {ident}_tenant_canonical IF NOT EXISTS "
            f"FOR (n:{nt.name}) ON (n.tenant_id, n.canonical_name)"
        )
    return statements


def to_json_schema(ontology: Ontology) -> Dict[str, object]:
    """JSON Schema for the graph.write MCP tool's mutation payload (RFC-001 §3.2)."""
    node_type_names = [nt.name for nt in ontology.node_types]
    relationship_names = [rt.name for rt in ontology.relation_types]

    node_schema: Dict[str, object] = {
        "type": "object",
        "required": ["id", "type", "canonical_name"],
        "properties": {
            "id": {"type": "string"},
            "type": {"enum": node_type_names},
            "canonical_name": {"type": "string"},
            "metadata": {"type": "object"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "tier": {"enum": ["staging", "trusted"], "default": "staging"},
        },
    }

    edge_schema: Dict[str, object] = {
        "type": "object",
        "required": ["source_id", "source_type", "target_id", "target_type", "relationship"],
        "properties": {
            "source_id": {"type": "string"},
            "source_type": {"enum": node_type_names},
            "target_id": {"type": "string"},
            "target_type": {"enum": node_type_names},
            "relationship": {"enum": relationship_names},
            "weight": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_spans": {"type": "array"},
        },
    }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"graph.write mutation payload (ontology v{ontology.version})",
        "type": "object",
        "required": ["mutations", "provenance"],
        "properties": {
            "mutations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["op"],
                    "properties": {
                        "op": {"enum": ["upsert_node", "upsert_edge", "deprecate"]},
                        "node": node_schema,
                        "edge": edge_schema,
                    },
                },
            },
            "provenance": dict(_PROVENANCE_SCHEMA),
        },
    }
