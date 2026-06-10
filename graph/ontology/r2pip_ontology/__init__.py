"""r2pip_ontology — versioned ontology-as-code for the R2P-IP knowledge graph."""

from .export import to_cypher, to_json_schema
from .loader import OntologyError, build_ontology, load_ontology
from .models import (
    EdgeInstance,
    NodeInstance,
    NodeTypeDef,
    Ontology,
    Provenance,
    RelationTypeDef,
)
from .validate import validate_edge, validate_mutation_batch, validate_node

__all__ = [
    "EdgeInstance",
    "NodeInstance",
    "NodeTypeDef",
    "Ontology",
    "OntologyError",
    "Provenance",
    "RelationTypeDef",
    "build_ontology",
    "load_ontology",
    "to_cypher",
    "to_json_schema",
    "validate_edge",
    "validate_mutation_batch",
    "validate_node",
]

__version__ = "1.0.0"
