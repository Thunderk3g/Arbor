from __future__ import annotations

from r2pip_audit.chain import (
    GENESIS_HASH,
    canonical_bytes,
    compute_event_hash,
    segment_merkle_root,
    verify_chain,
)
from r2pip_audit.models import Action


def build_chain(store, actor, action, context, tenant="t1", n=5):
    return [store.append(tenant, actor, action, context) for _ in range(n)]


def rehash(event):
    """Consistently recompute event_hash after tampering (relinking attack)."""
    return event.model_copy(update={"event_hash": compute_event_hash(event)})


def test_chain_links_and_genesis(store, actor, action, context):
    events = build_chain(store, actor, action, context)
    assert events[0].prev_hash == GENESIS_HASH
    for prev, cur in zip(events, events[1:]):
        assert cur.prev_hash == prev.event_hash


def test_canonical_bytes_excludes_event_hash_and_is_deterministic(
    store, actor, action, context
):
    event = store.append("t1", actor, action, context)
    raw = canonical_bytes(event)
    assert b"event_hash" not in raw
    assert raw == canonical_bytes(event.model_dump())
    assert compute_event_hash(event) == event.event_hash


def test_verify_chain_passes_on_honest_chain(store, actor, action, context):
    events = build_chain(store, actor, action, context, n=10)
    result = verify_chain(events)
    assert result.valid
    assert result.length == 10
    assert result.first_bad_seq is None
    assert result.reason is None


def test_verify_empty_chain_is_valid():
    result = verify_chain([])
    assert result.valid and result.length == 0


def test_tampered_middle_event_detected(store, actor, action, context):
    events = build_chain(store, actor, action, context, n=5)
    tampered = events[2].model_copy(
        update={"action": Action(type="deploy", tool="deploy.release")}
    )
    forged = events[:2] + [tampered] + events[3:]
    result = verify_chain(forged)
    assert not result.valid
    assert result.first_bad_seq == 3
    assert result.reason == "event_hash_mismatch"


def test_relinking_attack_detected_on_next_event(store, actor, action, context):
    events = build_chain(store, actor, action, context, n=5)
    tampered = rehash(
        events[2].model_copy(update={"action": Action(type="deploy")})
    )
    forged = events[:2] + [tampered] + events[3:]
    result = verify_chain(forged)
    assert not result.valid
    assert result.first_bad_seq == 4  # broken link surfaces on the successor
    assert result.reason == "broken_link"


def test_non_monotonic_seq_detected(store, actor, action, context):
    events = build_chain(store, actor, action, context, n=4)
    forged = [events[0], events[1], events[1], events[2]]
    result = verify_chain(forged)
    assert not result.valid
    assert result.reason == "non_monotonic_seq"
    assert result.first_bad_seq == 2


def test_merkle_root_deterministic_and_sensitive(store, actor, action, context):
    events = build_chain(store, actor, action, context, n=5)  # odd count
    root1 = segment_merkle_root(events)
    root2 = segment_merkle_root(events)
    assert root1 == root2
    assert len(root1) == 64

    tampered = rehash(events[1].model_copy(update={"action": Action(type="login")}))
    changed = events[:1] + [tampered] + events[2:]
    assert segment_merkle_root(changed) != root1
    assert segment_merkle_root(events[:4]) != root1


def test_merkle_root_empty_segment():
    assert segment_merkle_root([]) == GENESIS_HASH
