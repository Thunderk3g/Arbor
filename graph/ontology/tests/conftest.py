import pytest

from ontology_helpers import V1_PATH

from r2pip_ontology import Provenance, load_ontology


@pytest.fixture(scope="session")
def ontology():
    return load_ontology(V1_PATH)


@pytest.fixture
def trusted_provenance():
    return Provenance(
        source_type="human",
        source_ref="curation-queue/123",
        extractor="curator-ui@1.0",
        confidence=0.99,
        taint="trusted",
    )


@pytest.fixture
def untrusted_provenance():
    return Provenance(
        source_type="paper",
        source_ref="arxiv:2401.00001",
        extractor="claude-extractor@2.1/prompt-v3",
        confidence=0.8,
        taint="external_untrusted",
    )
