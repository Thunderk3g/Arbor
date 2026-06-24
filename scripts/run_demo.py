"""Launcher for the golden-mission demo without installing the packages.

Adds the six slice package roots plus the platform root to ``sys.path`` and runs
``r2pip_platform.demo``. Usage from the repo root:

    python scripts/run_demo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_PACKAGE_ROOTS = [
    "backend/audit",
    "backend/approval",
    "backend/gateway",
    "graph/focal",
    "graph/ontology",
    "memory",
    "platform",
]

for rel in _PACKAGE_ROOTS:
    path = str(_ROOT / rel)
    if path not in sys.path:
        sys.path.insert(0, path)

from r2pip_platform.demo import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
