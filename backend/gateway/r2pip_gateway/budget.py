"""Per-principal budget governor (gateway pipeline step 3). Thread-safe."""

from __future__ import annotations

import threading
from typing import Dict, Optional


class BudgetGovernor:
    """Tracks call counts per principal id against configured max_calls limits.

    Principals without a configured limit are unmetered (allowed). Consumption
    and the limit check are a single atomic step under one lock.
    """

    def __init__(self, limits: Optional[Dict[str, int]] = None) -> None:
        self._limits: Dict[str, int] = dict(limits or {})
        self._counts: Dict[str, int] = {}
        self._lock = threading.Lock()

    def set_limit(self, principal_id: str, max_calls: int) -> None:
        with self._lock:
            self._limits[principal_id] = max_calls

    def check_and_consume(self, principal_id: str) -> bool:
        with self._lock:
            limit = self._limits.get(principal_id)
            used = self._counts.get(principal_id, 0)
            if limit is not None and used >= limit:
                return False
            self._counts[principal_id] = used + 1
            return True

    def remaining(self, principal_id: str) -> Optional[int]:
        """Remaining calls, or None if the principal is unmetered."""
        with self._lock:
            limit = self._limits.get(principal_id)
            if limit is None:
                return None
            return max(0, limit - self._counts.get(principal_id, 0))
