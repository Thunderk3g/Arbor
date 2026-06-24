"""Shared builders for gateway tests (uniquely named — not a conftest import)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from r2pip_approval import ApprovalDecision, ApprovalService
from r2pip_approval.keys import generate_keypair
from r2pip_audit import InMemoryAuditStore

from r2pip_gateway import (
    BudgetGovernor,
    CallContext,
    Gateway,
    PolicyEngine,
    Principal,
    ToolDef,
    ToolRegistry,
    compute_params_hash,
)

TENANT = "tenant-1"


class GatewayStack:
    """A fully wired gateway with the real audit store and approval service."""

    def __init__(self, budget_limits: Optional[Dict[str, int]] = None) -> None:
        private_key, _public_key = generate_keypair()
        self.approvals = ApprovalService(private_key)
        self.audit = InMemoryAuditStore()
        self.budget = BudgetGovernor(budget_limits)
        self.registry = ToolRegistry()
        self.policy = PolicyEngine(approval_verifier=self.approvals.verify)
        self.gateway = Gateway(self.registry, self.policy, self.budget, self.audit)
        # (tool_name, args, credential) for every executed handler call.
        self.handler_calls: List[Tuple[str, Dict[str, Any], str]] = []
        self._register_sample_tools()

    def _register_sample_tools(self) -> None:
        def record(name: str):
            def handler(args: Dict[str, Any], credential: str) -> Dict[str, Any]:
                self.handler_calls.append((name, args, credential))
                return {"tool": name, "echo": args, "credential": credential}

            return handler

        def ast_handler(args: Dict[str, Any], credential: str) -> Dict[str, Any]:
            if args.get("code") == "BOOM":
                raise ValueError("parser exploded")
            self.handler_calls.append(("ast.analyze", args, credential))
            return {"symbols": [], "credential": credential}

        self.registry.register(
            ToolDef(
                name="research.search",
                family="perception",
                risk_class="low",
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {"query": {"type": "string"}},
                },
                handler=record("research.search"),
            )
        )
        self.registry.register(
            ToolDef(
                name="ast.analyze",
                family="computation",
                risk_class="low",
                input_schema={
                    "type": "object",
                    "required": ["code"],
                    "properties": {"code": {"type": "string"}},
                },
                handler=ast_handler,
            )
        )
        self.registry.register(
            ToolDef(
                name="deploy.release",
                family="action",
                risk_class="high",
                requires_approval=True,
                input_schema={
                    "type": "object",
                    "required": ["service", "revision"],
                    "properties": {
                        "service": {"type": "string"},
                        "revision": {"type": "string"},
                        "strategy": {
                            "type": "string",
                            "enum": ["canary", "blue_green"],
                        },
                    },
                },
                handler=record("deploy.release"),
            )
        )
        self.registry.register(
            ToolDef(
                name="deploy.rollback",
                family="action",
                risk_class="low",
                input_schema={
                    "type": "object",
                    "required": ["service"],
                    "properties": {"service": {"type": "string"}},
                },
                handler=record("deploy.rollback"),
            )
        )
        self.registry.register(
            ToolDef(
                name="graph.write",
                family="memory",
                risk_class="medium",
                input_schema={
                    "type": "object",
                    "required": ["mutations"],
                    "properties": {
                        "mutations": {"type": "array"},
                        "provenance": {"type": "object"},
                        "tier": {"type": "string"},
                    },
                },
                handler=record("graph.write"),
            )
        )

    def approval_token_for(self, args: Dict[str, Any]) -> str:
        """Create + approve a real approval request bound to these exact args."""
        request = self.approvals.create_request(
            tenant_id=TENANT,
            checkpoint="H5",
            action_type="deploy.release",
            subject_id=str(args.get("service", "svc")),
            params_hash=compute_params_hash(args),
            risk_score=0.7,
        )
        outcome = self.approvals.decide(
            request.id, ApprovalDecision(approver_id="human-operator", decision="approve")
        )
        assert outcome.token is not None
        return outcome.token


def agent(role: str = "developer_agent", principal_id: str = "agent-1") -> Principal:
    return Principal(kind="agent", id=principal_id, role=role)


def ctx(**overrides: Any) -> CallContext:
    return CallContext(tenant_id=TENANT, **overrides)
