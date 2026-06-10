import pytest

from r2pip_approval.keys import generate_keypair
from r2pip_approval.service import ApprovalService


@pytest.fixture
def keypair():
    return generate_keypair()


@pytest.fixture
def service(keypair):
    private_key, _ = keypair
    return ApprovalService(private_key, token_ttl_seconds=900)
