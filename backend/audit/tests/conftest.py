from __future__ import annotations

import pytest

from r2pip_audit.models import Action, Actor, EventContext
from r2pip_audit.store import InMemoryAuditStore


@pytest.fixture
def store() -> InMemoryAuditStore:
    return InMemoryAuditStore()


@pytest.fixture
def actor() -> Actor:
    return Actor(kind="agent", id="agent-codegen-1", on_behalf_of_mission="m-42")


@pytest.fixture
def action() -> Action:
    return Action(type="tool_call", tool="graph.read", params_hash="ab" * 32)


@pytest.fixture
def context() -> EventContext:
    return EventContext(mission_id="m-42", task_id="t-7", trace_id="tr-1")
