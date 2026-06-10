import pytest
from fastapi.testclient import TestClient

from r2pip_approval.app import create_app


@pytest.fixture
def client(service):
    return TestClient(create_app(service))


CREATE_BODY = {
    "tenant_id": "tenant-1",
    "checkpoint": "H5",
    "action_type": "deploy",
    "subject_id": "svc-payments",
    "params_hash": "a" * 64,
    "risk_score": 0.4,
    "evidence_bundle": {"revision": "rev-A"},
}


def test_full_round_trip(client):
    resp = client.post("/v1/approvals", json=CREATE_BODY)
    assert resp.status_code == 201
    request = resp.json()
    assert request["status"] == "pending"
    assert request["id"]

    resp = client.post(
        f"/v1/approvals/{request['id']}/decision",
        json={"approver_id": "alice", "decision": "approve"},
    )
    assert resp.status_code == 200
    outcome = resp.json()
    assert outcome["request"]["status"] == "approved"
    token = outcome["token"]
    assert token

    resp = client.post(
        "/v1/approvals/verify",
        json={"token": token, "params_hash": CREATE_BODY["params_hash"]},
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["valid"] is True
    assert result["approver"] == "alice"
    assert result["checkpoint"] == "H5"

    resp = client.post(
        "/v1/approvals/verify",
        json={"token": token, "params_hash": CREATE_BODY["params_hash"]},
    )
    assert resp.json() == {
        "valid": False,
        "reason": "token_already_used",
        "approver": None,
        "checkpoint": None,
    }


def test_create_destructive_without_consequence_422(client):
    body = dict(CREATE_BODY, destructive=True)
    resp = client.post("/v1/approvals", json=body)
    assert resp.status_code == 422


def test_decision_on_unknown_request_404(client):
    resp = client.post(
        "/v1/approvals/missing/decision",
        json={"approver_id": "alice", "decision": "approve"},
    )
    assert resp.status_code == 404


def test_decision_on_rejected_request_409(client):
    request = client.post("/v1/approvals", json=CREATE_BODY).json()
    client.post(
        f"/v1/approvals/{request['id']}/decision",
        json={"approver_id": "alice", "decision": "reject"},
    )
    resp = client.post(
        f"/v1/approvals/{request['id']}/decision",
        json={"approver_id": "bob", "decision": "approve"},
    )
    assert resp.status_code == 409


def test_verify_garbage_token(client):
    resp = client.post(
        "/v1/approvals/verify",
        json={"token": "not-a-jwt", "params_hash": "a" * 64},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is False
    assert resp.json()["reason"] == "invalid_token"
