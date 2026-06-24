"""r2pip_platform — the integration layer that composes the six R2P-IP reference
slices (audit, approval, gateway, focal, memory, ontology) into a runnable
platform that executes an end-to-end mission (RFC-001 §5, the golden mission
``examples/mission-walkthrough.md``).

Nothing here invents new infrastructure: every guarantee the demo shows —
hash-chained audit, taint firewall, single-use approval tokens, focal briefs —
is enforced by the underlying slice packages. This package only *wires* them
and drives the supervised-swarm mission workflow.

Reference implementation per ADR-011: in-memory, deterministic, pytest is the
behavioral contract for the future Go/Temporal port.
"""

from r2pip_platform.system import Platform, build_platform
from r2pip_platform.types import (
    GateContext,
    MissionResult,
    MissionSpec,
    MissionState,
    Role,
    StageRecord,
)

__all__ = [
    "GateContext",
    "MissionResult",
    "MissionSpec",
    "MissionState",
    "Platform",
    "Role",
    "StageRecord",
    "build_platform",
]
