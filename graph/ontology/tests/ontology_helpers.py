from pathlib import Path

V1_PATH = Path(__file__).resolve().parents[1] / "schemas" / "ontology-v1.yaml"


def minimal_ontology_data():
    return {
        "version": 99,
        "layers": ["research", "code"],
        "node_types": [
            {"name": "Method", "layer": "research", "required_metadata": ["description"]},
            {"name": "CodeBlock", "layer": "code", "required_metadata": ["language"]},
        ],
        "relation_types": [
            {
                "name": "IMPLEMENTS",
                "source_types": ["CodeBlock"],
                "target_types": ["Method"],
                "cross_layer": True,
            },
        ],
    }
