"""Tests for SessionMemoryStore: TTL with fake clock, checkpoint/restore."""

import json

from memory_helpers import FakeClock, claim, ledger_entry, task_memory
from r2pip_memory.models import TaskMemory
from r2pip_memory.store import SessionMemoryStore


class TestTTL:
    def test_get_before_expiry(self):
        clock = FakeClock()
        store = SessionMemoryStore(clock=clock)
        store.put("k", "v", ttl_seconds=10)
        clock.advance(9)
        assert store.get("k") == "v"

    def test_expired_returns_none(self):
        clock = FakeClock()
        store = SessionMemoryStore(clock=clock)
        store.put("k", "v", ttl_seconds=10)
        clock.advance(11)
        assert store.get("k") is None

    def test_no_ttl_never_expires(self):
        clock = FakeClock()
        store = SessionMemoryStore(clock=clock)
        store.put("k", "v")
        clock.advance(10_000_000)
        assert store.get("k") == "v"

    def test_missing_key_is_none(self):
        assert SessionMemoryStore(clock=FakeClock()).get("nope") is None


class TestAppendList:
    def test_creates_and_appends(self):
        store = SessionMemoryStore(clock=FakeClock())
        store.append_list("hypotheses", "h1")
        store.append_list("hypotheses", "h2")
        assert store.get("hypotheses") == ["h1", "h2"]


class TestCheckpointRestore:
    def _populated(self, clock):
        tm = task_memory(
            task_id="task-42",
            tool_ledger=[
                ledger_entry("led-1", tool="code.search", params_hash="deadbeefcafe", seq=1),
                ledger_entry("led-2", tool="tests.run", params_hash="0123456789ab",
                             result_status="error", seq=2),
            ],
            claims=[claim("searched the repo", "led-1")],
        )
        store = SessionMemoryStore(clock=clock)
        store.put("task_memory", tm)
        store.put("decisions", ["use redis"], ttl_seconds=None)
        store.put("scratch", {"open_questions": ["q1"]})
        return store, tm

    def test_snapshot_is_json_serializable(self):
        clock = FakeClock()
        store, _ = self._populated(clock)
        snapshot = store.checkpoint()
        json.dumps(snapshot)  # must not raise

    def test_round_trip_preserves_task_memory(self):
        clock = FakeClock()
        store, tm = self._populated(clock)
        snapshot = json.loads(json.dumps(store.checkpoint()))

        restored = SessionMemoryStore(clock=clock)
        restored.restore(snapshot)
        got = restored.get("task_memory")
        assert isinstance(got, TaskMemory)
        assert got == tm
        assert restored.get("decisions") == ["use redis"]
        assert restored.get("scratch") == {"open_questions": ["q1"]}

    def test_ttl_survives_round_trip(self):
        clock = FakeClock()
        store = SessionMemoryStore(clock=clock)
        store.put("ephemeral", "v", ttl_seconds=10)
        snapshot = store.checkpoint()

        restored = SessionMemoryStore(clock=clock)
        restored.restore(snapshot)
        assert restored.get("ephemeral") == "v"
        clock.advance(11)
        assert restored.get("ephemeral") is None

    def test_expired_entries_not_checkpointed(self):
        clock = FakeClock()
        store = SessionMemoryStore(clock=clock)
        store.put("ephemeral", "v", ttl_seconds=10)
        clock.advance(11)
        assert store.checkpoint()["entries"] == {}
