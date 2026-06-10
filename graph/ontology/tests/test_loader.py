import pytest

from r2pip_ontology import OntologyError, build_ontology, load_ontology

from ontology_helpers import V1_PATH, minimal_ontology_data

EXPECTED_NODE_TYPES = {
    # research
    "ResearchPaper", "Claim", "Method", "Dataset", "Metric", "Author", "Institution",
    # code
    "Repository", "CodeBlock", "Interface", "Dependency", "TestCase", "SoftwareArtifact",
    # market
    "Company", "Product", "MarketSignal", "Segment", "Need",
    # platform
    "Opportunity", "Hypothesis", "ARS", "Task", "DeploymentRecord", "AgentEpisode",
}

EXPECTED_RELATION_TYPES = {
    "CITES", "IMPROVES_ON", "CONTRADICTS", "EVALUATED_ON", "IMPLEMENTS",
    "DEPENDS_ON", "COMPETES_WITH", "SIGNALS_DEMAND_FOR", "ADDRESSES",
    "IMPLEMENTABLE_AS", "SAME_AS_CANDIDATE", "AUTHORED_BY", "AFFILIATED_WITH",
}


class TestV1Loads:
    def test_loads_clean(self):
        ontology = load_ontology(V1_PATH)
        assert ontology.version == 1

    def test_counts_match_spec(self, ontology):
        assert len(ontology.node_types) == 24
        assert len(ontology.relation_types) == 13
        assert {nt.name for nt in ontology.node_types} == EXPECTED_NODE_TYPES
        assert {rt.name for rt in ontology.relation_types} == EXPECTED_RELATION_TYPES

    def test_layers(self, ontology):
        assert ontology.layers == ["research", "code", "market", "platform"]
        assert all(nt.layer in ontology.layers for nt in ontology.node_types)

    def test_lookup_maps(self, ontology):
        assert ontology.node_types_by_name["Method"].layer == "research"
        assert ontology.relation_types_by_name["IMPLEMENTS"].cross_layer is True

    def test_cross_layer_flags(self, ontology):
        cross = {rt.name for rt in ontology.relation_types if rt.cross_layer}
        assert cross == {"IMPLEMENTS", "SIGNALS_DEMAND_FOR", "ADDRESSES", "IMPLEMENTABLE_AS"}


class TestLoaderValidation:
    def test_duplicate_node_type_name(self):
        data = minimal_ontology_data()
        data["node_types"].append(
            {"name": "Method", "layer": "research", "required_metadata": []}
        )
        with pytest.raises(OntologyError, match="Duplicate node type name: 'Method'"):
            build_ontology(data)

    def test_duplicate_relation_type_name(self):
        data = minimal_ontology_data()
        data["relation_types"].append(dict(data["relation_types"][0]))
        with pytest.raises(OntologyError, match="Duplicate relation type name"):
            build_ontology(data)

    def test_relation_with_unknown_endpoint(self):
        data = minimal_ontology_data()
        data["relation_types"].append(
            {
                "name": "BAD_EDGE",
                "source_types": ["Method"],
                "target_types": ["Ghost"],
                "cross_layer": False,
            }
        )
        with pytest.raises(OntologyError, match="unknown target node type 'Ghost'"):
            build_ontology(data)

    def test_node_with_unknown_layer(self):
        data = minimal_ontology_data()
        data["node_types"].append(
            {"name": "Rogue", "layer": "shadow", "required_metadata": []}
        )
        with pytest.raises(OntologyError, match="unknown layer 'shadow'"):
            build_ontology(data)

    def test_undeclared_cross_layer_relation(self):
        data = minimal_ontology_data()
        data["relation_types"][0]["cross_layer"] = False
        with pytest.raises(OntologyError, match="spanning layers.*not declared cross_layer"):
            build_ontology(data)

    def test_cross_layer_declared_but_same_layer(self):
        data = minimal_ontology_data()
        data["relation_types"].append(
            {
                "name": "REFINES",
                "source_types": ["Method"],
                "target_types": ["Method"],
                "cross_layer": True,
            }
        )
        with pytest.raises(OntologyError, match="declared cross_layer=true but no"):
            build_ontology(data)
