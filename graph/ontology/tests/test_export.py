from r2pip_ontology import to_cypher, to_json_schema


class TestToCypher:
    def test_one_uniqueness_constraint_per_node_type(self, ontology):
        statements = to_cypher(ontology)
        constraints = [s for s in statements if s.startswith("CREATE CONSTRAINT")]
        assert len(constraints) == len(ontology.node_types) == 24

    def test_one_index_per_node_type(self, ontology):
        statements = to_cypher(ontology)
        indexes = [s for s in statements if s.startswith("CREATE INDEX")]
        assert len(indexes) == 24
        assert all("(n.tenant_id, n.canonical_name)" in s for s in indexes)

    def test_spot_check_constraint_string(self, ontology):
        statements = to_cypher(ontology)
        assert (
            "CREATE CONSTRAINT researchpaper_id_unique IF NOT EXISTS "
            "FOR (n:ResearchPaper) REQUIRE n.id IS UNIQUE"
        ) in statements

    def test_spot_check_index_string(self, ontology):
        statements = to_cypher(ontology)
        assert (
            "CREATE INDEX method_tenant_canonical IF NOT EXISTS "
            "FOR (n:Method) ON (n.tenant_id, n.canonical_name)"
        ) in statements


class TestToJsonSchema:
    def test_top_level_shape(self, ontology):
        schema = to_json_schema(ontology)
        assert schema["type"] == "object"
        assert set(schema["required"]) == {"mutations", "provenance"}
        assert "mutations" in schema["properties"]
        assert "provenance" in schema["properties"]

    def test_provenance_block(self, ontology):
        prov = to_json_schema(ontology)["properties"]["provenance"]
        assert prov["type"] == "object"
        assert set(prov["required"]) == {"source_type", "source_ref", "extractor", "confidence"}
        assert prov["properties"]["taint"]["enum"] == ["trusted", "external_untrusted"]

    def test_relationship_enum_matches_ontology(self, ontology):
        schema = to_json_schema(ontology)
        edge = schema["properties"]["mutations"]["items"]["properties"]["edge"]
        assert set(edge["properties"]["relationship"]["enum"]) == {
            rt.name for rt in ontology.relation_types
        }

    def test_node_type_enum_matches_ontology(self, ontology):
        schema = to_json_schema(ontology)
        node = schema["properties"]["mutations"]["items"]["properties"]["node"]
        assert set(node["properties"]["type"]["enum"]) == {
            nt.name for nt in ontology.node_types
        }

    def test_op_enum(self, ontology):
        schema = to_json_schema(ontology)
        items = schema["properties"]["mutations"]["items"]
        assert items["properties"]["op"]["enum"] == ["upsert_node", "upsert_edge", "deprecate"]
