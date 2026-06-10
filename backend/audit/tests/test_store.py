from __future__ import annotations

import threading

from r2pip_audit.chain import GENESIS_HASH, verify_chain
from r2pip_audit.models import Action, Actor, EventContext


def test_append_assigns_monotonic_seq(store, actor, action, context):
    events = [store.append("t1", actor, action, context) for _ in range(5)]
    assert [e.seq for e in events] == [1, 2, 3, 4, 5]
    assert store.count("t1") == 5
    assert store.head("t1").seq == 5


def test_tenants_have_independent_chains(store, actor, action, context):
    a1 = store.append("tenant-a", actor, action, context)
    b1 = store.append("tenant-b", actor, action, context)
    a2 = store.append("tenant-a", actor, action, context)

    assert a1.seq == 1 and b1.seq == 1 and a2.seq == 2
    assert a1.prev_hash == GENESIS_HASH
    assert b1.prev_hash == GENESIS_HASH
    assert a2.prev_hash == a1.event_hash
    assert verify_chain(store.get_events("tenant-a")).valid
    assert verify_chain(store.get_events("tenant-b")).valid


def test_caller_supplied_ts_is_kept(store, actor, action, context):
    ts = "2026-06-10T00:00:00+00:00"
    event = store.append("t1", actor, action, context, ts=ts)
    assert event.ts == ts


def test_get_events_filters(store, context):
    human = Actor(kind="human", id="u1")
    agent = Actor(kind="agent", id="a1")
    store.append("t1", human, Action(type="login"), context)
    store.append("t1", agent, Action(type="tool_call", tool="x"), context)
    store.append("t1", agent, Action(type="deploy"), context)

    assert [e.seq for e in store.get_events("t1", actor_kind="agent")] == [2, 3]
    assert [e.seq for e in store.get_events("t1", action_type="login")] == [1]
    assert [e.seq for e in store.get_events("t1", from_seq=2, to_seq=2)] == [2]
    assert store.get_events("missing-tenant") == []


def test_concurrent_appends_yield_valid_chain(store, actor, action, context):
    n_threads, per_thread = 8, 25  # 200 events total
    barrier = threading.Barrier(n_threads)

    def worker():
        barrier.wait()
        for _ in range(per_thread):
            store.append("t1", actor, action, context)

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    events = store.get_events("t1")
    assert len(events) == n_threads * per_thread
    seqs = [e.seq for e in events]
    assert seqs == list(range(1, n_threads * per_thread + 1))
    assert len(set(seqs)) == len(seqs)
    result = verify_chain(events)
    assert result.valid and result.length == 200


def test_default_context_taint_is_trusted():
    assert EventContext().taint == "trusted"
