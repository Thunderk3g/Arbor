"""Hash-chain core: canonical serialization, event hashing, chain verification, Merkle roots."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Optional, Sequence, Union

from pydantic import BaseModel

from .models import AuditEvent

GENESIS_HASH = "0" * 64


def canonical_bytes(event_fields: Union[Mapping[str, Any], AuditEvent]) -> bytes:
    """Deterministic JSON (sorted keys, no whitespace, UTF-8) of all fields except event_hash."""
    if isinstance(event_fields, BaseModel):
        fields: dict[str, Any] = event_fields.model_dump()
    else:
        fields = {
            k: (v.model_dump() if isinstance(v, BaseModel) else v)
            for k, v in event_fields.items()
        }
    fields.pop("event_hash", None)
    return json.dumps(
        fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def compute_event_hash(event_without_hash: Union[Mapping[str, Any], AuditEvent]) -> str:
    return hashlib.sha256(canonical_bytes(event_without_hash)).hexdigest()


class ChainVerification(BaseModel):
    valid: bool
    length: int
    first_bad_seq: Optional[int] = None
    reason: Optional[str] = None


def verify_chain(events: Sequence[AuditEvent]) -> ChainVerification:
    prev_seq: Optional[int] = None
    prev_hash = GENESIS_HASH
    for event in events:
        if prev_seq is not None and event.seq <= prev_seq:
            return ChainVerification(
                valid=False,
                length=len(events),
                first_bad_seq=event.seq,
                reason="non_monotonic_seq",
            )
        if compute_event_hash(event) != event.event_hash:
            return ChainVerification(
                valid=False,
                length=len(events),
                first_bad_seq=event.seq,
                reason="event_hash_mismatch",
            )
        if event.prev_hash != prev_hash:
            return ChainVerification(
                valid=False,
                length=len(events),
                first_bad_seq=event.seq,
                reason="broken_link",
            )
        prev_seq = event.seq
        prev_hash = event.event_hash
    return ChainVerification(valid=True, length=len(events))


def segment_merkle_root(events: Sequence[AuditEvent]) -> str:
    """SHA-256 Merkle root over event_hash leaves; odd levels duplicate the last node."""
    if not events:
        return GENESIS_HASH
    level = [bytes.fromhex(e.event_hash) for e in events]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [
            hashlib.sha256(level[i] + level[i + 1]).digest()
            for i in range(0, len(level), 2)
        ]
    return level[0].hex()
