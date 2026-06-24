"""Shared contracts for the orchestration layer (cross tools/agents/mission).

These are the fixed types every subsystem builds against. Pure pydantic v2;
the only slice import is the approval ``ApprovalDecision`` re-exported for the
gate-approver callback signature.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    """Roles in the supervised swarm (RFC-001 §2.2). The string value is the
    gateway ``Principal.role`` and the audit actor id suffix."""

    BI = "bi_agent"
    PO = "po_agent"
    HEAD_ENGINEER = "head_engineer"
    DEVELOPER = "developer"
    QA = "qa_agent"
    INFRA = "infra_agent"


class MissionSpec(BaseModel):
    """The input to a mission: an opportunity seed plus its delivery target."""

    tenant_id: str
    title: str
    # Seed knowledge-graph node ids the BI sweep starts from (market signal etc).
    opportunity_seed_ids: list[str] = Field(default_factory=list)
    # The service/repository the mission will modify.
    target_service: str = "svc-pricing"
    target_repo_node: str = "repo-svc-pricing"
    # Image digest the deploy will be bound to (stands in for the CI build output).
    image_digest: str = "sha256:9f2c0000000000000000000000000000000000000000000000000000000000aa"


class StageRecord(BaseModel):
    """One stage of the mission workflow (RFC-001 §5 stages 0-13)."""

    stage: str
    status: str  # "ok" | "blocked" | "rejected" | "error"
    summary: str = ""
    audit_seqs: list[int] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)


class GateContext(BaseModel):
    """Everything a human needs to decide a HITL checkpoint (RFC-001 §1.7, §7.3)."""

    checkpoint: str  # "H1" | "H2" | "H5"
    title: str
    subject_id: str
    risk_score: float = 0.0
    evidence: dict[str, Any] = Field(default_factory=dict)
    destructive: bool = False
    required_consequence: Optional[str] = None
    dual_control: bool = False


class MissionState(BaseModel):
    """Accumulated mission state — the orchestrator's working record."""

    spec: MissionSpec
    status: str = "running"  # "running" | "completed" | "aborted" | "error"
    stages: list[StageRecord] = Field(default_factory=list)
    opportunity_id: Optional[str] = None
    ars_id: Optional[str] = None
    risk_score: Optional[float] = None
    autonomy_mode: Optional[str] = None
    claims_sheet: Optional[str] = None
    merged: bool = False
    deployed: bool = False
    abort_reason: Optional[str] = None

    def record(self, stage: StageRecord) -> StageRecord:
        self.stages.append(stage)
        return stage


class MissionResult(BaseModel):
    """The terminal output of a mission run, including the forensic answers
    the audit trail can produce (mission-walkthrough.md, closing section)."""

    mission_id: str
    state: MissionState
    audit_length: int
    chain_valid: bool
    forensics: dict[str, str] = Field(default_factory=dict)


# A scripted/human approver: given a gate, return an ApprovalDecision.
# Typed as Callable[[GateContext], "ApprovalDecision"]; imported lazily by the
# orchestrator to avoid a hard import cycle at module load.
ApproverFn = Callable[[GateContext], Any]
