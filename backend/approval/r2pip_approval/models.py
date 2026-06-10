"""Pydantic models for the Approval Service (ADR-009, RFC-001 §7.3)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

Checkpoint = Literal["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApprovalDecision(BaseModel):
    approver_id: str
    decision: Literal["approve", "reject"]
    typed_consequence: Optional[str] = None
    comment: Optional[str] = None
    decided_at: datetime = Field(default_factory=_utcnow)


class ApprovalRequest(BaseModel):
    id: str
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
    status: Literal["pending", "approved", "rejected", "expired"] = "pending"
    approvals: List[ApprovalDecision] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)

    @model_validator(mode="after")
    def _destructive_requires_consequence(self) -> "ApprovalRequest":
        if self.destructive and not self.required_consequence:
            raise ValueError(
                "destructive approvals require a required_consequence string"
            )
        return self


class VerificationResult(BaseModel):
    valid: bool
    reason: Optional[str] = None
    approver: Optional[str] = None
    checkpoint: Optional[str] = None
