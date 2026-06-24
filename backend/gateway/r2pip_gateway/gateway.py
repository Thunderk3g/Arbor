"""Gateway: the single choke point for all tool calls (RFC-001 §3.3, ADR-004).

Pipeline per invoke:
  1. resolve tool + schema validation
  2. policy evaluation (taint firewall lives inside policy)
  3. quota/budget check
  4. credential injection (scoped, short-lived — stubbed)
  5. execute handler
  6. result taint-tagging
  7. exactly one hash-chained audit event per invoke (including denials/errors)
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from r2pip_audit import Action, Actor, AuditStore, EventContext
from pydantic import BaseModel

from .budget import BudgetGovernor
from .policy import CallContext, PolicyEngine, Principal, compute_params_hash
from .registry import ToolRegistry
from .validation import validate_args


class GatewayResult(BaseModel):
    status: Literal["ok", "denied", "error"]
    reason: Optional[str] = None
    result: Any = None
    result_taint: Optional[str] = None
    audit_seq: int


class Gateway:
    def __init__(
        self,
        registry: ToolRegistry,
        policy_engine: PolicyEngine,
        budget: BudgetGovernor,
        audit_store: AuditStore,
    ) -> None:
        self._registry = registry
        self._policy = policy_engine
        self._budget = budget
        self._audit = audit_store

    def invoke(
        self,
        principal: Principal,
        tool_name: str,
        args: dict,
        context: CallContext,
    ) -> GatewayResult:
        params_hash = compute_params_hash(args)
        tool = self._registry.get(tool_name)

        # 1. Schema validation (only resolvable tools have a schema).
        if tool is not None:
            violations = validate_args(args, tool.input_schema)
            if violations:
                return self._denied(
                    principal,
                    tool_name,
                    params_hash,
                    context,
                    f"schema_violation:{violations[0]}",
                )

        # 2. Policy (unknown tool, families, taint firewall, provenance,
        #    role scoping, approval gate — all inside the engine, in order).
        decision = self._policy.evaluate(principal, tool, args, context)
        if not decision.allow:
            return self._denied(principal, tool_name, params_hash, context, decision.reason)

        # 3. Budget.
        if not self._budget.check_and_consume(principal.id):
            return self._denied(
                principal, tool_name, params_hash, context, "budget_exhausted"
            )

        # 4. Credential injection (stub for the Vault-issued 15-min scoped cred).
        credential = f"scoped:{tool_name}:{principal.id}"

        # 5. Execute on the domain MCP server (handler stand-in).
        assert tool is not None  # policy denies unknown tools before this point
        try:
            result = tool.handler(args, credential)
        except Exception as exc:  # noqa: BLE001 — gateway must fail closed, not crash
            seq = self._append_audit(
                principal, tool_name, params_hash, context, action_type="tool_call"
            )
            return GatewayResult(
                status="error", reason=f"handler_error:{exc}", audit_seq=seq
            )

        # 6. Result taint-tagging: perception output is attacker-influenceable.
        result_taint = (
            "external_untrusted" if tool.family == "perception" else context.taint
        )

        # 7. Audit (executed call).
        seq = self._append_audit(
            principal, tool_name, params_hash, context, action_type="tool_call"
        )
        return GatewayResult(
            status="ok", result=result, result_taint=result_taint, audit_seq=seq
        )

    # --- internals ----------------------------------------------------------

    def _denied(
        self,
        principal: Principal,
        tool_name: str,
        params_hash: str,
        context: CallContext,
        reason: str,
    ) -> GatewayResult:
        seq = self._append_audit(
            principal, tool_name, params_hash, context, action_type="policy_decision"
        )
        return GatewayResult(status="denied", reason=reason, audit_seq=seq)

    def _append_audit(
        self,
        principal: Principal,
        tool_name: str,
        params_hash: str,
        context: CallContext,
        action_type: str,
    ) -> int:
        event = self._audit.append(
            tenant_id=context.tenant_id,
            actor=Actor(
                kind=principal.kind,
                id=principal.id,
                on_behalf_of_mission=context.mission_id,
            ),
            action=Action(type=action_type, tool=tool_name, params_hash=params_hash),
            context=EventContext(
                mission_id=context.mission_id,
                task_id=context.task_id,
                trace_id=context.trace_id,
                taint=context.taint,
            ),
        )
        return event.seq
