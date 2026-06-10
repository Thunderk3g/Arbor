"""r2pip_audit — hash-chained audit log reference implementation (RFC-001 §7.7)."""

from .chain import (
    GENESIS_HASH,
    ChainVerification,
    canonical_bytes,
    compute_event_hash,
    segment_merkle_root,
    verify_chain,
)
from .models import Action, Actor, AuditEvent, EventContext
from .store import AuditStore, InMemoryAuditStore

__all__ = [
    "Action",
    "Actor",
    "AuditEvent",
    "AuditStore",
    "ChainVerification",
    "EventContext",
    "GENESIS_HASH",
    "InMemoryAuditStore",
    "canonical_bytes",
    "compute_event_hash",
    "segment_merkle_root",
    "verify_chain",
]
