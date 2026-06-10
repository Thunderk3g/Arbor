"""Audit store protocol and thread-safe in-memory implementation."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol, runtime_checkable

from .chain import GENESIS_HASH, compute_event_hash
from .models import Action, Actor, AuditEvent, EventContext


@runtime_checkable
class AuditStore(Protocol):
    def append(
        self,
        tenant_id: str,
        actor: Actor,
        action: Action,
        context: EventContext,
        ts: Optional[str] = None,
    ) -> AuditEvent: ...

    def get_events(
        self,
        tenant_id: str,
        from_seq: Optional[int] = None,
        to_seq: Optional[int] = None,
        actor_kind: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> List[AuditEvent]: ...

    def head(self, tenant_id: str) -> Optional[AuditEvent]: ...

    def count(self, tenant_id: str) -> int: ...


class InMemoryAuditStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._chains: Dict[str, List[AuditEvent]] = {}

    def append(
        self,
        tenant_id: str,
        actor: Actor,
        action: Action,
        context: EventContext,
        ts: Optional[str] = None,
    ) -> AuditEvent:
        if ts is None:
            ts = datetime.now(timezone.utc).isoformat()
        # Seq assignment, prev_hash linkage, and storage must be one atomic step.
        with self._lock:
            chain = self._chains.setdefault(tenant_id, [])
            seq = len(chain) + 1
            prev_hash = chain[-1].event_hash if chain else GENESIS_HASH
            fields = {
                "event_id": str(uuid.uuid4()),
                "seq": seq,
                "tenant_id": tenant_id,
                "actor": actor,
                "action": action,
                "context": context,
                "ts": ts,
                "prev_hash": prev_hash,
            }
            event = AuditEvent(event_hash=compute_event_hash(fields), **fields)
            chain.append(event)
            return event

    def get_events(
        self,
        tenant_id: str,
        from_seq: Optional[int] = None,
        to_seq: Optional[int] = None,
        actor_kind: Optional[str] = None,
        action_type: Optional[str] = None,
    ) -> List[AuditEvent]:
        with self._lock:
            chain = list(self._chains.get(tenant_id, []))
        result = []
        for event in chain:
            if from_seq is not None and event.seq < from_seq:
                continue
            if to_seq is not None and event.seq > to_seq:
                continue
            if actor_kind is not None and event.actor.kind != actor_kind:
                continue
            if action_type is not None and event.action.type != action_type:
                continue
            result.append(event)
        return result

    def head(self, tenant_id: str) -> Optional[AuditEvent]:
        with self._lock:
            chain = self._chains.get(tenant_id)
            return chain[-1] if chain else None

    def count(self, tenant_id: str) -> int:
        with self._lock:
            return len(self._chains.get(tenant_id, []))
