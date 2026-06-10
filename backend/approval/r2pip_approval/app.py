"""FastAPI app factory for the Approval Service (RFC-001 §7.3)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from r2pip_approval.models import (
    ApprovalDecision,
    ApprovalRequest,
    Checkpoint,
    VerificationResult,
)
from r2pip_approval.service import ApprovalService, DecisionOutcome


class CreateApprovalBody(BaseModel):
    tenant_id: str
    checkpoint: Checkpoint
    action_type: str
    subject_id: str
    params_hash: str
    risk_score: float = Field(ge=0.0, le=1.0)
    evidence_bundle: Dict[str, Any] = Field(default_factory=dict)
    destructive: bool = False
    required_consequence: Optional[str] = None
    dual_control: bool = False


class VerifyBody(BaseModel):
    token: str
    params_hash: str


def create_app(service: ApprovalService) -> FastAPI:
    app = FastAPI(title="R2P-IP Approval Service")

    @app.post("/v1/approvals", response_model=ApprovalRequest, status_code=201)
    def create_approval(body: CreateApprovalBody) -> ApprovalRequest:
        try:
            return service.create_request(**body.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/v1/approvals/{request_id}/decision", response_model=DecisionOutcome)
    def decide(request_id: str, decision: ApprovalDecision) -> DecisionOutcome:
        try:
            return service.decide(request_id, decision)
        except KeyError:
            raise HTTPException(status_code=404, detail="approval request not found")
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))

    @app.post("/v1/approvals/verify", response_model=VerificationResult)
    def verify(body: VerifyBody) -> VerificationResult:
        return service.verify(body.token, body.params_hash)

    return app
