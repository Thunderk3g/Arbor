"""Agent runtime (RFC-001 §2.3, §4.1, Appendix B).

One ``AgentRuntime`` wraps one agent's principal, its prompt assembler, and its
per-task memory. It enforces the platform-level disciplines that Appendix B
makes non-optional:

* Every turn's prompt is **built, never accreted** (the assembler) and its hash
  is written to the audit log as a ``prompt`` event — "log every prompt".
* Every tool call goes through the gateway and is recorded in the task's tool
  ledger — the evidence base for grounded claims (B.4).
* Untrusted content rides in as a fenced ``tool_results``/``focal`` segment, so
  the turn that holds it is marked tainted in both the prompt audit event and
  the gateway call context — and the taint firewall does the rest.
* ``fresh_context`` rebuilds a turn from scratch (B.5 / §2.3 fresh-context
  retry): the volatile scratchpad is dropped, durable evidence (the ledger) is
  kept.
"""

from __future__ import annotations

from typing import Optional

from r2pip_audit import Action, Actor
from r2pip_gateway import CallContext, GatewayResult, Principal, compute_params_hash
from r2pip_memory import MemorySegment, PromptAssembler, TaskMemory, ToolLedgerEntry

from r2pip_platform.types import Role

_SEGMENT_BUDGETS = {
    "system": 500,
    "ars": 1000,
    "focal": 4000,
    "exemplars": 1000,
    "task_memory": 1500,
    "tool_results": 2500,
}
_TOTAL_BUDGET = 9000


class AgentRuntime:
    def __init__(self, platform, role: Role, agent_id: str) -> None:
        self.platform = platform
        self.role = role
        self.agent_id = agent_id
        self.principal = Principal(kind="agent", id=agent_id, role=role.value)
        self.assembler = PromptAssembler(_SEGMENT_BUDGETS, _TOTAL_BUDGET)
        self._memories: dict[str, TaskMemory] = {}
        self._ledger_counter = 0
        self._seq_counter = 0

    # --- task memory -------------------------------------------------------

    def task_memory(self, task_id: str) -> TaskMemory:
        return self._memories.setdefault(task_id, TaskMemory(task_id=task_id))

    def fresh_context(self, task_id: str) -> TaskMemory:
        """Start a clean turn: drop volatile hypotheses/attempts, keep the
        audited tool ledger and claims (durable evidence)."""
        tm = self.task_memory(task_id)
        tm.hypotheses.clear()
        tm.attempts.clear()
        return tm

    # --- thinking (prompt assembly + audit) --------------------------------

    def think(
        self,
        *,
        mission_id: str,
        task_id: str,
        trace_id: str,
        system: str,
        ars: Optional[str] = None,
        focal_context: Optional[str] = None,
        focal_taint: str = "trusted",
        untrusted_data: Optional[str] = None,
    ):
        """Assemble this turn's prompt and audit it. Returns the AssembledPrompt.

        ``untrusted_data`` (e.g. fetched paper text) is included as a fenced
        ``tool_results`` DATA segment; its presence taints the whole turn.
        """
        self._seq_counter += 1
        base = self._seq_counter * 10
        segments = [
            MemorySegment(kind="system", content=system, relevance=1.0, created_seq=base),
        ]
        if ars:
            segments.append(
                MemorySegment(kind="ars", content=ars, relevance=0.9, created_seq=base + 1)
            )
        if focal_context:
            segments.append(
                MemorySegment(
                    kind="focal", content=focal_context, relevance=0.85,
                    created_seq=base + 2, taint=focal_taint,
                )
            )
        if untrusted_data:
            segments.append(
                MemorySegment(
                    kind="tool_results", content=untrusted_data, relevance=0.7,
                    created_seq=base + 3, taint="external_untrusted",
                )
            )

        turn_taint = (
            "external_untrusted"
            if (untrusted_data or focal_taint == "external_untrusted")
            else "trusted"
        )
        prompt = self.assembler.assemble(segments)
        self.platform.audit_event(
            actor=Actor(kind="agent", id=self.agent_id, on_behalf_of_mission=mission_id),
            action=Action(type="prompt", tool=None, content_ref=prompt.prompt_hash),
            mission_id=mission_id,
            task_id=task_id,
            trace_id=trace_id,
            taint=turn_taint,
        )
        return prompt

    # --- acting (gateway tool call + ledger) -------------------------------

    def call(
        self,
        tool: str,
        args: dict,
        *,
        mission_id: str,
        task_id: str,
        trace_id: str,
        taint: str = "trusted",
        approval_token: Optional[str] = None,
    ) -> GatewayResult:
        ctx = CallContext(
            tenant_id=self.platform.tenant_id,
            mission_id=mission_id,
            task_id=task_id,
            trace_id=trace_id,
            taint=taint,
            approval_token=approval_token,
        )
        result = self.platform.gateway.invoke(self.principal, tool, args, ctx)
        self._ledger_counter += 1
        self.task_memory(task_id).tool_ledger.append(
            ToolLedgerEntry(
                ledger_id=f"{self.agent_id}-L{self._ledger_counter}",
                tool=tool,
                params_hash=compute_params_hash(args),
                result_status=result.status,
                summary=(result.reason or "ok")[:120],
                seq=result.audit_seq,
            )
        )
        return result

    def last_ledger_id(self, task_id: str) -> Optional[str]:
        ledger = self.task_memory(task_id).tool_ledger
        return ledger[-1].ledger_id if ledger else None
