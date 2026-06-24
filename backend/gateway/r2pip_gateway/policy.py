"""Policy engine: ordered rules over (principal, tool, args, context) — RFC-001 §7.2.

Mirrors the OPA/Rego policy at the Go gateway. Rules are evaluated in a fixed
order; the first rule that produces a decision wins. The taint-based tool
firewall (ADR-008) is deliberately evaluated *before* the approval gate so an
untrusted context can never consume (or be rescued by) a valid approval token.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel

from .registry import ToolDef

Taint = Literal["trusted", "external_untrusted"]

# Memory tools whose invocation writes to the knowledge substrate.
_MEMORY_WRITE_PREFIXES = ("graph.write", "vector.upsert")
# Tool name prefixes scoped to the infra_agent role.
_INFRA_SCOPED_PREFIXES = ("deploy.", "infra.")


def compute_params_hash(args: Dict[str, Any]) -> str:
    """Canonical sha256 of the call args — the binding used by approval tokens."""
    canonical = json.dumps(args, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _requests_trusted_tier(value: Any) -> bool:
    """True if a ``"tier": "trusted"`` appears anywhere in the call args — at the
    top level OR nested inside a node/edge spec. Checking only the top-level key
    let an untrusted turn mint a trusted-tier node by hiding ``tier`` inside the
    node payload; scanning the whole structure closes that bypass (ADR-008)."""
    if isinstance(value, dict):
        if value.get("tier") == "trusted":
            return True
        return any(_requests_trusted_tier(v) for v in value.values())
    if isinstance(value, list):
        return any(_requests_trusted_tier(item) for item in value)
    return False


class Principal(BaseModel):
    kind: Literal["human", "agent", "system"]
    id: str
    role: str


class CallContext(BaseModel):
    tenant_id: str
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    trace_id: Optional[str] = None
    taint: Taint = "trusted"
    approval_token: Optional[str] = None


class PolicyDecision(BaseModel):
    allow: bool
    reason: str
    policy: str


# An injected verifier: verify(token, params_hash) -> object with .valid and .reason
ApprovalVerifier = Callable[[str, str], Any]

_Rule = Callable[[Principal, ToolDef, Dict[str, Any], CallContext], Optional[PolicyDecision]]


class PolicyEngine:
    def __init__(self, approval_verifier: Optional[ApprovalVerifier] = None) -> None:
        self._verify = approval_verifier
        self._rules: List[Tuple[str, _Rule]] = [
            ("taint_firewall", self._rule_taint_firewall),
            ("perception_computation", self._rule_perception_computation),
            ("memory_provenance", self._rule_memory),
            ("role_scope", self._rule_role_scope),
            ("approval_gate", self._rule_approval_gate),
            ("action_low_risk", self._rule_action_low_risk),
        ]

    def evaluate(
        self,
        principal: Principal,
        tool: Optional[ToolDef],
        args: Dict[str, Any],
        context: CallContext,
    ) -> PolicyDecision:
        if tool is None:
            return PolicyDecision(allow=False, reason="unknown_tool", policy="unknown_tool")
        for _name, rule in self._rules:
            decision = rule(principal, tool, args, context)
            if decision is not None:
                return decision
        return PolicyDecision(
            allow=False, reason="no_matching_policy", policy="default_deny"
        )

    # --- ordered rules -----------------------------------------------------

    @staticmethod
    def _rule_taint_firewall(
        principal: Principal, tool: ToolDef, args: Dict[str, Any], context: CallContext
    ) -> Optional[PolicyDecision]:
        """ADR-008: untrusted taint blocks all Action tools and trusted-tier memory writes."""
        if context.taint != "external_untrusted":
            return None
        if tool.family == "action":
            return PolicyDecision(
                allow=False, reason="taint_firewall", policy="taint_firewall"
            )
        if tool.family == "memory" and _requests_trusted_tier(args):
            return PolicyDecision(
                allow=False, reason="taint_firewall", policy="taint_firewall"
            )
        return None

    @staticmethod
    def _rule_perception_computation(
        principal: Principal, tool: ToolDef, args: Dict[str, Any], context: CallContext
    ) -> Optional[PolicyDecision]:
        if tool.family in ("perception", "computation") and principal.kind == "agent":
            return PolicyDecision(
                allow=True,
                reason="family_allowed",
                policy="perception_computation",
            )
        return None

    @staticmethod
    def _rule_memory(
        principal: Principal, tool: ToolDef, args: Dict[str, Any], context: CallContext
    ) -> Optional[PolicyDecision]:
        if tool.family != "memory":
            return None
        if tool.name.startswith(_MEMORY_WRITE_PREFIXES) and "provenance" not in args:
            return PolicyDecision(
                allow=False, reason="provenance_required", policy="memory_provenance"
            )
        if principal.kind == "agent":
            return PolicyDecision(
                allow=True, reason="memory_allowed", policy="memory_provenance"
            )
        return None

    @staticmethod
    def _rule_role_scope(
        principal: Principal, tool: ToolDef, args: Dict[str, Any], context: CallContext
    ) -> Optional[PolicyDecision]:
        if not tool.name.startswith(_INFRA_SCOPED_PREFIXES):
            return None
        if principal.role != "infra_agent":
            return PolicyDecision(
                allow=False, reason="role_forbidden", policy="role_scope"
            )
        if tool.name == "deploy.rollback":
            # Pre-authorized for infra_agent (RFC §3.1): no approval token required.
            return PolicyDecision(
                allow=True, reason="preauthorized_rollback", policy="role_scope"
            )
        return None

    def _rule_approval_gate(
        self, principal: Principal, tool: ToolDef, args: Dict[str, Any], context: CallContext
    ) -> Optional[PolicyDecision]:
        if tool.family != "action":
            return None
        needs_approval = (
            tool.risk_class in ("high", "destructive") or tool.requires_approval
        )
        if not needs_approval:
            return None
        token = context.approval_token
        if not token:
            return PolicyDecision(
                allow=False, reason="approval_required", policy="approval_gate"
            )
        if self._verify is None:
            return PolicyDecision(
                allow=False,
                reason="approval_invalid:no_verifier_configured",
                policy="approval_gate",
            )
        result = self._verify(token, compute_params_hash(args))
        if not result.valid:
            return PolicyDecision(
                allow=False,
                reason=f"approval_invalid:{result.reason}",
                policy="approval_gate",
            )
        return PolicyDecision(
            allow=True, reason="approval_verified", policy="approval_gate"
        )

    @staticmethod
    def _rule_action_low_risk(
        principal: Principal, tool: ToolDef, args: Dict[str, Any], context: CallContext
    ) -> Optional[PolicyDecision]:
        if (
            tool.family == "action"
            and principal.kind == "agent"
            and tool.risk_class in ("low", "medium")
            and not tool.requires_approval
        ):
            return PolicyDecision(
                allow=True, reason="action_allowed", policy="action_low_risk"
            )
        return None
