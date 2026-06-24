"""Unified FastAPI surface for the R2P-IP reference platform (RFC-001 §10).

Exposes the platform as a service: list the tool plane, run the golden mission,
inspect and verify the audit chain. Each ``POST /missions/run`` executes against
a *fresh* platform (its own audit chain and signing key) so runs are isolated
and reproducible — the demo's whole point is that the guarantees hold per run,
not that state accretes across them.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from r2pip_audit import verify_chain
from r2pip_platform import MissionSpec, build_platform
from r2pip_platform.corpus import OPPORTUNITY_SEEDS
from r2pip_platform.mission import MissionOrchestrator, scripted_approver
from r2pip_platform.types import MissionResult


class RunMissionRequest(BaseModel):
    title: str = "Add electrolyte cycle-life prediction to acme's pricing API"
    tenant_id: str = "acme-energy"


def create_app() -> FastAPI:
    app = FastAPI(title="R2P-IP Reference Platform", version="0.1.0")
    # A long-lived platform for read-only introspection (tools, health).
    info_platform = build_platform()

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "tenant": info_platform.tenant_id,
            "tools": len(info_platform.registry.list()),
            "graph_nodes": len(info_platform.graph.nodes),
        }

    @app.get("/tools")
    def tools() -> dict:
        return {
            "tools": [
                {
                    "name": t.name,
                    "family": t.family,
                    "risk_class": t.risk_class,
                    "requires_approval": t.requires_approval,
                }
                for t in sorted(info_platform.registry.list(), key=lambda t: t.name)
            ]
        }

    @app.post("/missions/run", response_model=MissionResult)
    def run_mission(req: RunMissionRequest) -> MissionResult:
        platform = build_platform(req.tenant_id)
        spec = MissionSpec(
            tenant_id=req.tenant_id,
            title=req.title,
            opportunity_seed_ids=OPPORTUNITY_SEEDS,
        )
        return MissionOrchestrator(platform, scripted_approver).run(spec)

    @app.get("/audit/verify")
    def audit_verify() -> dict:
        events = info_platform.audit.get_events(info_platform.tenant_id)
        v = verify_chain(events)
        return {"length": v.length, "valid": v.valid, "reason": v.reason}

    return app


app = create_app()
