"""Shared builders for platform integration tests.

Uniquely named (not ``conftest``) and imported directly, per the suite's
import-mode=importlib + no-conftest-import convention.
"""

from __future__ import annotations

from r2pip_gateway import CallContext, Principal

from r2pip_platform import MissionSpec, build_platform
from r2pip_platform.corpus import OPPORTUNITY_SEEDS
from r2pip_platform.mission import MissionOrchestrator, scripted_approver


def make_platform():
    return build_platform("acme-energy")


def make_spec(**overrides) -> MissionSpec:
    params = dict(
        tenant_id="acme-energy",
        title="Add electrolyte cycle-life prediction to acme's pricing API",
        opportunity_seed_ids=OPPORTUNITY_SEEDS,
    )
    params.update(overrides)
    return MissionSpec(**params)


def run_golden_mission(approver=scripted_approver, *, platform=None):
    platform = platform or make_platform()
    orch = MissionOrchestrator(platform, approver)
    return platform, orch, orch.run(make_spec())


def agent_principal(agent_id="bi-agent", role="po_agent") -> Principal:
    return Principal(kind="agent", id=agent_id, role=role)


def ctx(platform, *, taint="trusted", approval_token=None) -> CallContext:
    return CallContext(
        tenant_id=platform.tenant_id,
        mission_id="MSN-TEST",
        task_id="T",
        trace_id="tr",
        taint=taint,
        approval_token=approval_token,
    )
