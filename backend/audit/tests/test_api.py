from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from r2pip_audit.app import create_app
from r2pip_audit.chain import GENESIS_HASH
from r2pip_audit.store import InMemoryAuditStore


@pytest.fixture
def client():
    return TestClient(create_app(InMemoryAuditStore()))


def event_body(tenant="t1", action_type="tool_call", actor_kind="agent"):
    return {
        "tenant_id": tenant,
        "actor": {"kind": actor_kind, "id": "a1", "on_behalf_of_mission": "m-1"},
        "action": {"type": action_type, "tool": "graph.read", "params_hash": "cd" * 32},
        "context": {"mission_id": "m-1", "task_id": "t-1", "taint": "trusted"},
    }


def test_post_event_seals_and_returns_201(client):
    resp = client.post("/v1/audit/events", json=event_body())
    assert resp.status_code == 201
    event = resp.json()
    assert event["seq"] == 1
    assert event["prev_hash"] == GENESIS_HASH
    assert len(event["event_hash"]) == 64
    assert event["event_id"]
    assert event["ts"]


def test_round_trip_get_and_verify(client):
    for i in range(4):
        action_type = "deploy" if i == 3 else "tool_call"
        resp = client.post("/v1/audit/events", json=event_body(action_type=action_type))
        assert resp.status_code == 201

    resp = client.get("/v1/audit/events", params={"tenant_id": "t1"})
    assert resp.status_code == 200
    events = resp.json()["events"]
    assert [e["seq"] for e in events] == [1, 2, 3, 4]
    for prev, cur in zip(events, events[1:]):
        assert cur["prev_hash"] == prev["event_hash"]

    resp = client.get(
        "/v1/audit/events", params={"tenant_id": "t1", "action_type": "deploy"}
    )
    assert [e["seq"] for e in resp.json()["events"]] == [4]

    resp = client.get(
        "/v1/audit/events", params={"tenant_id": "t1", "from_seq": 2, "to_seq": 3}
    )
    assert [e["seq"] for e in resp.json()["events"]] == [2, 3]

    resp = client.post("/v1/audit/verify", json={"tenant_id": "t1"})
    assert resp.status_code == 200
    verification = resp.json()
    assert verification["valid"] is True
    assert verification["length"] == 4


def test_segment_root_endpoint(client):
    for _ in range(3):
        client.post("/v1/audit/events", json=event_body())

    resp = client.get("/v1/audit/segments/root", params={"tenant_id": "t1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 3
    assert len(body["merkle_root"]) == 64

    sub = client.get(
        "/v1/audit/segments/root",
        params={"tenant_id": "t1", "from_seq": 1, "to_seq": 2},
    ).json()
    assert sub["count"] == 2
    assert sub["merkle_root"] != body["merkle_root"]

    empty = client.get(
        "/v1/audit/segments/root", params={"tenant_id": "nope"}
    ).json()
    assert empty == {"merkle_root": GENESIS_HASH, "count": 0}


def test_invalid_actor_kind_rejected(client):
    body = event_body()
    body["actor"]["kind"] = "alien"
    resp = client.post("/v1/audit/events", json=body)
    assert resp.status_code == 422
