"""ApprovalService: issues and verifies signed single-use approval tokens (ADR-009)."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Set

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel

from r2pip_approval.models import (
    ApprovalDecision,
    ApprovalRequest,
    Checkpoint,
    VerificationResult,
)

_ALGORITHM = "EdDSA"


class DecisionOutcome(BaseModel):
    request: ApprovalRequest
    token: Optional[str] = None


class ApprovalService:
    def __init__(
        self, private_key: Ed25519PrivateKey, token_ttl_seconds: int = 900
    ) -> None:
        self._private_key = private_key
        self._public_key = private_key.public_key()
        self._token_ttl_seconds = token_ttl_seconds
        self._requests: Dict[str, ApprovalRequest] = {}
        self._consumed_jtis: Set[str] = set()
        self._lock = threading.Lock()

    def create_request(
        self,
        *,
        tenant_id: str,
        checkpoint: Checkpoint,
        action_type: str,
        subject_id: str,
        params_hash: str,
        risk_score: float,
        evidence_bundle: Optional[Dict[str, Any]] = None,
        destructive: bool = False,
        required_consequence: Optional[str] = None,
        dual_control: bool = False,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            checkpoint=checkpoint,
            action_type=action_type,
            subject_id=subject_id,
            params_hash=params_hash,
            risk_score=risk_score,
            evidence_bundle=evidence_bundle or {},
            destructive=destructive,
            required_consequence=required_consequence,
            dual_control=dual_control,
        )
        with self._lock:
            self._requests[request.id] = request
        return request

    def get_request(self, request_id: str) -> ApprovalRequest:
        with self._lock:
            return self._requests[request_id]

    def decide(self, request_id: str, decision: ApprovalDecision) -> DecisionOutcome:
        with self._lock:
            request = self._requests[request_id]
            if request.status != "pending":
                raise ValueError(
                    f"request {request_id} is {request.status}, not pending"
                )

            if decision.decision == "reject":
                request.approvals.append(decision)
                request.status = "rejected"
                return DecisionOutcome(request=request, token=None)

            if request.destructive:
                if decision.typed_consequence != request.required_consequence:
                    request.approvals.append(
                        decision.model_copy(update={"decision": "reject"})
                    )
                    request.status = "rejected"
                    raise ValueError(
                        "typed_consequence does not exactly match "
                        "required_consequence; approval rejected"
                    )

            prior_approvers = {
                a.approver_id for a in request.approvals if a.decision == "approve"
            }
            if decision.approver_id in prior_approvers:
                raise ValueError(
                    f"approver {decision.approver_id} has already approved; "
                    "dual control requires two distinct humans"
                )

            request.approvals.append(decision)
            approvers = [
                a.approver_id for a in request.approvals if a.decision == "approve"
            ]

            if request.dual_control and len(approvers) < 2:
                return DecisionOutcome(request=request, token=None)

            request.status = "approved"
            token = self._issue_token(request, approvers)
            return DecisionOutcome(request=request, token=token)

    def _issue_token(self, request: ApprovalRequest, approvers: list) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "jti": str(uuid.uuid4()),
            "checkpoint": request.checkpoint,
            "action_type": request.action_type,
            "params_hash": request.params_hash,
            "approver": ",".join(approvers),
            "tenant_id": request.tenant_id,
            "iat": now,
            "exp": now + timedelta(seconds=self._token_ttl_seconds),
            "single_use": True,
        }
        return jwt.encode(claims, self._private_key, algorithm=_ALGORITHM)

    def verify(self, token: str, params_hash: str) -> VerificationResult:
        try:
            claims = jwt.decode(
                token,
                self._public_key,
                algorithms=[_ALGORITHM],
                options={"require": ["jti", "exp", "iat"]},
            )
        except jwt.ExpiredSignatureError:
            return VerificationResult(valid=False, reason="expired")
        except jwt.InvalidTokenError:
            return VerificationResult(valid=False, reason="invalid_token")

        if claims.get("params_hash") != params_hash:
            return VerificationResult(valid=False, reason="params_mismatch")

        jti = claims["jti"]
        with self._lock:
            if jti in self._consumed_jtis:
                return VerificationResult(valid=False, reason="token_already_used")
            self._consumed_jtis.add(jti)

        return VerificationResult(
            valid=True,
            reason=None,
            approver=claims.get("approver"),
            checkpoint=claims.get("checkpoint"),
        )
