"""Load and structurally validate an ontology YAML definition."""

from __future__ import annotations

from pathlib import Path
from typing import List, Union

import yaml
from pydantic import ValidationError

from .models import WILDCARD, NodeTypeDef, Ontology, RelationTypeDef


class OntologyError(Exception):
    """Raised when an ontology definition is structurally invalid."""


def _check_duplicates(names: List[str], kind: str) -> None:
    seen = set()
    for name in names:
        if name in seen:
            raise OntologyError(f"Duplicate {kind} type name: {name!r}")
        seen.add(name)


def _check_layers(node_types: List[NodeTypeDef], layers: List[str]) -> None:
    for nt in node_types:
        if nt.layer not in layers:
            raise OntologyError(
                f"Node type {nt.name!r} references unknown layer {nt.layer!r}; "
                f"known layers: {layers}"
            )


def _check_relation_endpoints(
    relation_types: List[RelationTypeDef], known_nodes: set
) -> None:
    for rt in relation_types:
        for endpoint, side in [(s, "source") for s in rt.source_types] + [
            (t, "target") for t in rt.target_types
        ]:
            if endpoint != WILDCARD and endpoint not in known_nodes:
                raise OntologyError(
                    f"Relation type {rt.name!r} references unknown {side} "
                    f"node type {endpoint!r}"
                )


def _check_cross_layer(
    relation_types: List[RelationTypeDef], node_types: List[NodeTypeDef]
) -> None:
    layer_of = {nt.name: nt.layer for nt in node_types}
    for rt in relation_types:
        if WILDCARD in rt.source_types or WILDCARD in rt.target_types:
            continue
        spans = any(
            layer_of[s] != layer_of[t]
            for s in rt.source_types
            for t in rt.target_types
        )
        if spans and not rt.cross_layer:
            raise OntologyError(
                f"Relation type {rt.name!r} has endpoints spanning layers but is "
                f"not declared cross_layer=true"
            )
        if rt.cross_layer and not spans:
            raise OntologyError(
                f"Relation type {rt.name!r} is declared cross_layer=true but no "
                f"source/target pair spans layers"
            )


def build_ontology(data: dict) -> Ontology:
    """Construct and validate an Ontology from already-parsed YAML data."""
    try:
        node_types = [NodeTypeDef(**nt) for nt in data.get("node_types", [])]
        relation_types = [RelationTypeDef(**rt) for rt in data.get("relation_types", [])]
    except ValidationError as exc:
        raise OntologyError(f"Malformed ontology definition: {exc}") from exc

    layers = data.get("layers", [])
    _check_duplicates([nt.name for nt in node_types], "node")
    _check_duplicates([rt.name for rt in relation_types], "relation")
    _check_layers(node_types, layers)
    _check_relation_endpoints(relation_types, {nt.name for nt in node_types})
    _check_cross_layer(relation_types, node_types)

    return Ontology(
        version=data.get("version", 0),
        layers=layers,
        node_types=node_types,
        relation_types=relation_types,
    )


def load_ontology(path: Union[str, Path]) -> Ontology:
    """Load an ontology YAML file, validating structure at load time."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise OntologyError(f"Ontology file {path} did not parse to a mapping")
    return build_ontology(data)
