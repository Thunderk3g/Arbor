"""Instance validation against a loaded ontology (RFC-001 §4.2, §4.5)."""

from __future__ import annotations

from typing import Dict, List, Sequence

from .models import EdgeInstance, NodeInstance, Ontology


def validate_node(node: NodeInstance, ontology: Ontology) -> List[str]:
    violations: List[str] = []

    type_def = ontology.node_types_by_name.get(node.type)
    if type_def is None:
        violations.append(f"unknown node type {node.type!r}")
    else:
        missing = [k for k in type_def.required_metadata if k not in node.metadata]
        for key in missing:
            violations.append(
                f"missing required metadata field {key!r} for node type {node.type!r}"
            )

    if node.provenance is None:
        violations.append("provenance is required for all node writes")

    if not 0.0 <= node.confidence <= 1.0:
        violations.append(
            f"confidence {node.confidence} out of range [0, 1]"
        )

    if node.tier == "trusted" and node.provenance is not None:
        if node.provenance.taint != "trusted":
            violations.append(
                "trusted tier requires provenance taint == 'trusted' "
                f"(got {node.provenance.taint!r})"
            )

    return violations


def validate_edge(edge: EdgeInstance, ontology: Ontology) -> List[str]:
    violations: List[str] = []

    rel_def = ontology.relation_types_by_name.get(edge.relationship)
    if rel_def is None:
        violations.append(f"unknown relationship {edge.relationship!r}")
    else:
        if not rel_def.allows_source(edge.source_type):
            violations.append(
                f"source type {edge.source_type!r} not allowed for "
                f"{edge.relationship}; allowed: {rel_def.source_types}"
            )
        if not rel_def.allows_target(edge.target_type):
            violations.append(
                f"target type {edge.target_type!r} not allowed for "
                f"{edge.relationship}; allowed: {rel_def.target_types}"
            )
        if rel_def.same_type_only and edge.source_type != edge.target_type:
            violations.append(
                f"{edge.relationship} requires source and target of the same type "
                f"(got {edge.source_type!r} -> {edge.target_type!r})"
            )

    for side, node_type in (("source", edge.source_type), ("target", edge.target_type)):
        if node_type not in ontology.node_types_by_name:
            violations.append(f"unknown {side} node type {node_type!r}")

    if edge.provenance is None:
        violations.append("provenance is required for all edge writes")

    if not 0.0 <= edge.weight <= 1.0:
        violations.append(f"weight {edge.weight} out of range [0, 1]")

    return violations


def validate_mutation_batch(
    nodes: Sequence[NodeInstance],
    edges: Sequence[EdgeInstance],
    ontology: Ontology,
) -> Dict[str, object]:
    violations: List[str] = []

    batch_types: Dict[str, str] = {n.id: n.type for n in nodes}

    for node in nodes:
        for v in validate_node(node, ontology):
            violations.append(f"node {node.id!r}: {v}")

    for edge in edges:
        label = f"edge {edge.source_id!r}-[{edge.relationship}]->{edge.target_id!r}"
        for v in validate_edge(edge, ontology):
            violations.append(f"{label}: {v}")
        for side, ref_id, declared in (
            ("source", edge.source_id, edge.source_type),
            ("target", edge.target_id, edge.target_type),
        ):
            batch_type = batch_types.get(ref_id)
            if batch_type is not None and batch_type != declared:
                violations.append(
                    f"{label}: {side} type {declared!r} does not match batch "
                    f"node {ref_id!r} of type {batch_type!r}"
                )

    return {"valid": not violations, "violations": violations}
