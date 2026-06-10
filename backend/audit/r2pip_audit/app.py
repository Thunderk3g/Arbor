"""FastAPI app factory for the Audit Service reference API."""

from __future__ import annotations

from typing import List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel

from .chain import ChainVerification, segment_merkle_root, verify_chain
from .models import Action, Actor, AuditEvent, EventContext
from .store import AuditStore, InMemoryAuditStore


class AppendEventRequest(BaseModel):
    tenant_id: str
    actor: Actor
    action: Action
    context: EventContext = EventContext()


class EventListResponse(BaseModel):
    events: List[AuditEvent]


class VerifyRequest(BaseModel):
    tenant_id: str


class SegmentRootResponse(BaseModel):
    merkle_root: str
    count: int


def create_app(store: Optional[AuditStore] = None) -> FastAPI:
    if store is None:
        store = InMemoryAuditStore()
    app = FastAPI(title="R2P-IP Audit Service", version="0.1.0")

    @app.post("/v1/audit/events", response_model=AuditEvent, status_code=201)
    def append_event(body: AppendEventRequest) -> AuditEvent:
        return store.append(body.tenant_id, body.actor, body.action, body.context)

    @app.get("/v1/audit/events", response_model=EventListResponse)
    def list_events(
        tenant_id: str = Query(...),
        from_seq: Optional[int] = Query(default=None),
        to_seq: Optional[int] = Query(default=None),
        actor_kind: Optional[str] = Query(default=None),
        action_type: Optional[str] = Query(default=None),
    ) -> EventListResponse:
        events = store.get_events(
            tenant_id,
            from_seq=from_seq,
            to_seq=to_seq,
            actor_kind=actor_kind,
            action_type=action_type,
        )
        return EventListResponse(events=events)

    @app.post("/v1/audit/verify", response_model=ChainVerification)
    def verify(body: VerifyRequest) -> ChainVerification:
        return verify_chain(store.get_events(body.tenant_id))

    @app.get("/v1/audit/segments/root", response_model=SegmentRootResponse)
    def segment_root(
        tenant_id: str = Query(...),
        from_seq: Optional[int] = Query(default=None),
        to_seq: Optional[int] = Query(default=None),
    ) -> SegmentRootResponse:
        events = store.get_events(tenant_id, from_seq=from_seq, to_seq=to_seq)
        return SegmentRootResponse(
            merkle_root=segment_merkle_root(events), count=len(events)
        )

    return app
