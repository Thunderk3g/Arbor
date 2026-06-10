"""Pydantic models for the R2P-IP knowledge-graph ontology (RFC-001 §4)."""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, PrivateAttr

WILDCARD = "*"

SourceType = Literal["paper", "market_feed", "telemetry", "agent_inference", "human"]
Taint = Literal["trusted", "external_untrusted"]
Tier = Literal["staging", "trusted"]


class NodeTypeDef(BaseModel):
    name: str
    layer: str
    required_metadata: List[str] = Field(default_factory=list)
    description: str = ""


class RelationTypeDef(BaseModel):
    name: str
    source_types: List[str]
    target_types: List[str]
    description: str = ""
    cross_layer: bool = False
    same_type_only: bool = False

    def allows_source(self, node_type: str) -> bool:
        return WILDCARD in self.source_types or node_type in self.source_types

    def allows_target(self, node_type: str) -> bool:
        return WILDCARD in self.target_types or node_type in self.target_types


class Ontology(BaseModel):
    version: int
    layers: List[str]
    node_types: List[NodeTypeDef]
    relation_types: List[RelationTypeDef]

    _node_types_by_name: Dict[str, NodeTypeDef] = PrivateAttr(default_factory=dict)
    _relation_types_by_name: Dict[str, RelationTypeDef] = PrivateAttr(default_factory=dict)

    def model_post_init(self, __context: object) -> None:
        self._node_types_by_name = {nt.name: nt for nt in self.node_types}
        self._relation_types_by_name = {rt.name: rt for rt in self.relation_types}

    @property
    def node_types_by_name(self) -> Dict[str, NodeTypeDef]:
        return self._node_types_by_name

    @property
    def relation_types_by_name(self) -> Dict[str, RelationTypeDef]:
        return self._relation_types_by_name


class Provenance(BaseModel):
    source_type: SourceType
    source_ref: str
    extractor: str
    confidence: float = Field(ge=0.0, le=1.0)
    taint: Taint = "external_untrusted"


class NodeInstance(BaseModel):
    id: str
    type: str
    canonical_name: str
    metadata: Dict[str, object] = Field(default_factory=dict)
    confidence: float = 0.0
    tier: Tier = "staging"
    provenance: Optional[Provenance] = None


class EdgeInstance(BaseModel):
    source_id: str
    source_type: str
    target_id: str
    target_type: str
    relationship: str
    weight: float = 1.0
    evidence_spans: List[object] = Field(default_factory=list)
    provenance: Optional[Provenance] = None
