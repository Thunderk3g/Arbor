"""Session memory store: TTL-bound key/value state with checkpoint/restore (§4.1).

Expiry uses an injectable clock callable so tests never sleep. Checkpoints are
plain JSON-serializable dicts; known pydantic models are tagged and rebuilt on
restore so a TaskMemory survives a round trip intact.
"""

import threading
import time
from typing import Any, Callable, Optional

from pydantic import BaseModel

from r2pip_memory.models import (
    AssembledPrompt,
    Claim,
    MemorySegment,
    TaskMemory,
    ToolLedgerEntry,
)

_MODEL_REGISTRY: dict[str, type[BaseModel]] = {
    cls.__name__: cls
    for cls in (MemorySegment, ToolLedgerEntry, Claim, TaskMemory, AssembledPrompt)
}

_MODEL_TAG = "__r2pip_model__"


def _dump(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return {_MODEL_TAG: type(value).__name__, "data": value.model_dump(mode="json")}
    if isinstance(value, list):
        return [_dump(v) for v in value]
    if isinstance(value, tuple):
        return [_dump(v) for v in value]
    if isinstance(value, dict):
        return {k: _dump(v) for k, v in value.items()}
    return value


def _load(value: Any) -> Any:
    if isinstance(value, dict):
        if _MODEL_TAG in value and value[_MODEL_TAG] in _MODEL_REGISTRY:
            return _MODEL_REGISTRY[value[_MODEL_TAG]].model_validate(value["data"])
        return {k: _load(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_load(v) for v in value]
    return value


class SessionMemoryStore:
    """Thread-safe per-mission session memory with TTL expiry."""

    def __init__(self, clock: Callable[[], float] = time.time):
        self._clock = clock
        self._lock = threading.Lock()
        self._entries: dict[str, tuple[Any, Optional[float]]] = {}

    def put(self, key: str, value: Any, ttl_seconds: Optional[float] = None) -> None:
        expires_at = None if ttl_seconds is None else self._clock() + ttl_seconds
        with self._lock:
            self._entries[key] = (value, expires_at)

    def get(self, key: str) -> Any:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and self._clock() >= expires_at:
                del self._entries[key]
                return None
            return value

    def append_list(self, key: str, item: Any) -> None:
        with self._lock:
            entry = self._entries.get(key)
            now = self._clock()
            if entry is not None:
                value, expires_at = entry
                if expires_at is not None and now >= expires_at:
                    entry = None
            if entry is None:
                self._entries[key] = ([item], None)
                return
            value, expires_at = entry
            if not isinstance(value, list):
                raise TypeError(f"key {key!r} does not hold a list")
            value.append(item)

    def checkpoint(self) -> dict:
        """Snapshot the store as a JSON-serializable dict (pydantic models dumped)."""
        with self._lock:
            now = self._clock()
            entries = {}
            for key, (value, expires_at) in self._entries.items():
                if expires_at is not None and now >= expires_at:
                    continue
                entries[key] = {"value": _dump(value), "expires_at": expires_at}
            return {"version": 1, "entries": entries}

    def restore(self, snapshot: dict) -> None:
        """Replace store contents from a checkpoint() snapshot."""
        with self._lock:
            self._entries = {
                key: (_load(entry["value"]), entry.get("expires_at"))
                for key, entry in snapshot.get("entries", {}).items()
            }
