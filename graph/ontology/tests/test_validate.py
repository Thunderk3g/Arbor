from r2pip_ontology import (
    EdgeInstance,
    NodeInstance,
    validate_edge,
    validate_mutation_batch,
    validate_node,
)


def make_method_node(provenance, **overrides):
    defaults = dict(
        id="method-1",
        type="Method",
        canonical_name="flash attention",
        metadata={"description": "IO-aware exact attention"},
        confidence=0.9,
        tier="staging",
        provenance=provenance,
    )
    defaults.update(overrides)
    return NodeInstance(**defaults)


def make_implements_edge(provenance, **overrides):
    defaults = dict(
        source_id="cb-1",
        source_type="CodeBlock",
        target_id="method-1",
        target_type="Method",
        relationship="IMPLEMENTS",
        weight=0.85,
        provenance=provenance,
    )
    defaults.update(overrides)
    return EdgeInstance(**defaults)


class TestValidateNode:
    def test_valid_node_passes(self, ontology, untrusted_provenance):
        node = make_method_node(untrusted_provenance)
        assert validate_node(node, ontology) == []

    def test_unknown_type(self, ontology, untrusted_provenance):
        node = make_method_node(untrusted_provenance, type="Gizmo")
        violations = validate_node(node, ontology)
        assert any("unknown node type 'Gizmo'" in v for v in violations)

    def test_missing_required_metadata_names_field(self, ontology, untrusted_provenance):
        node = make_method_node(untrusted_provenance, metadata={})
        violations = validate_node(node, ontology)
        assert any("'description'" in v and "missing required metadata" in v for v in violations)

    def test_missing_provenance(self, ontology):
        node = make_method_node(None)
        violations = validate_node(node, ontology)
        assert any("provenance is required" in v for v in violations)

    def test_confidence_out_of_range(self, ontology, untrusted_provenance):
        node = make_method_node(untrusted_provenance, confidence=1.5)
        violations = validate_node(node, ontology)
        assert any("out of range" in v for v in violations)

    def test_trusted_tier_with_untrusted_taint_fails(self, ontology, untrusted_provenance):
        node = make_method_node(untrusted_provenance, tier="trusted")
        violations = validate_node(node, ontology)
        assert any("taint" in v for v in violations)

    def test_trusted_tier_with_trusted_taint_passes(self, ontology, trusted_provenance):
        node = make_method_node(trusted_provenance, tier="trusted")
        assert validate_node(node, ontology) == []


class TestValidateEdge:
    def test_valid_implements_edge(self, ontology, untrusted_provenance):
        edge = make_implements_edge(untrusted_provenance)
        assert validate_edge(edge, ontology) == []

    def test_implements_swapped_endpoints_fails(self, ontology, untrusted_provenance):
        edge = make_implements_edge(
            untrusted_provenance,
            source_id="method-1",
            source_type="Method",
            target_id="cb-1",
            target_type="CodeBlock",
        )
        violations = validate_edge(edge, ontology)
        assert any("source type 'Method' not allowed" in v for v in violations)
        assert any("target type 'CodeBlock' not allowed" in v for v in violations)

    def test_unknown_relationship(self, ontology, untrusted_provenance):
        edge = make_implements_edge(untrusted_provenance, relationship="TELEPORTS_TO")
        violations = validate_edge(edge, ontology)
        assert any("unknown relationship 'TELEPORTS_TO'" in v for v in violations)

    def test_missing_provenance(self, ontology):
        edge = make_implements_edge(None)
        violations = validate_edge(edge, ontology)
        assert any("provenance is required" in v for v in violations)

    def test_weight_out_of_range(self, ontology, untrusted_provenance):
        edge = make_implements_edge(untrusted_provenance, weight=2.0)
        violations = validate_edge(edge, ontology)
        assert any("weight 2.0 out of range" in v for v in violations)

    def test_same_as_candidate_requires_same_type(self, ontology, untrusted_provenance):
        edge = make_implements_edge(
            untrusted_provenance,
            relationship="SAME_AS_CANDIDATE",
            source_type="Method",
            target_type="Company",
        )
        violations = validate_edge(edge, ontology)
        assert any("same type" in v for v in violations)

    def test_same_as_candidate_same_type_passes(self, ontology, untrusted_provenance):
        edge = make_implements_edge(
            untrusted_provenance,
            relationship="SAME_AS_CANDIDATE",
            source_type="Company",
            target_type="Company",
        )
        assert validate_edge(edge, ontology) == []


class TestValidateMutationBatch:
    def test_valid_batch(self, ontology, untrusted_provenance):
        code_node = NodeInstance(
            id="cb-1",
            type="CodeBlock",
            canonical_name="attn.forward",
            metadata={"language": "python", "symbol_path": "pkg/attn.py::forward"},
            confidence=0.9,
            provenance=untrusted_provenance,
        )
        method_node = make_method_node(untrusted_provenance)
        edge = make_implements_edge(untrusted_provenance)
        report = validate_mutation_batch([code_node, method_node], [edge], ontology)
        assert report["valid"] is True
        assert report["violations"] == []

    def test_batch_aggregates_node_and_edge_violations(self, ontology, untrusted_provenance):
        bad_node = make_method_node(None, metadata={})
        bad_edge = make_implements_edge(untrusted_provenance, weight=5.0)
        report = validate_mutation_batch([bad_node], [bad_edge], ontology)
        assert report["valid"] is False
        node_violations = [v for v in report["violations"] if v.startswith("node ")]
        edge_violations = [v for v in report["violations"] if v.startswith("edge ")]
        assert node_violations and edge_violations

    def test_edge_type_must_match_batch_node(self, ontology, untrusted_provenance):
        method_node = make_method_node(untrusted_provenance, id="n-1")
        edge = make_implements_edge(
            untrusted_provenance, source_id="n-1", source_type="CodeBlock"
        )
        report = validate_mutation_batch([method_node], [edge], ontology)
        assert report["valid"] is False
        assert any("does not match batch node" in v for v in report["violations"])
