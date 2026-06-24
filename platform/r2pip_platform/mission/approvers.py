"""Approver callbacks: turn a HITL gate into a human decision (RFC-001 §1.7).

In production these are real people clicking the approval inbox. For the
reproducible demo and tests they are pure functions ``GateContext ->
ApprovalDecision``. The scripted approver mirrors the walkthrough cast (Priya at
H1, Marcus at H2/H4, Dana at H5) and always supplies the exact typed consequence
for destructive gates, so the happy path completes deterministically.
"""

from __future__ import annotations

from typing import Optional

from r2pip_approval.models import ApprovalDecision

from r2pip_platform.types import GateContext

# Walkthrough cast: which human owns which checkpoint.
_GATE_OWNERS = {
    "H1": "priya",
    "H2": "marcus",
    "H4": "marcus",
    "H5": "dana",
}


def _approve(gate: GateContext, approver_id: str) -> ApprovalDecision:
    return ApprovalDecision(
        approver_id=approver_id,
        decision="approve",
        # For destructive gates, echo the required consequence exactly.
        typed_consequence=gate.required_consequence if gate.destructive else None,
    )


def scripted_approver(gate: GateContext) -> ApprovalDecision:
    """Approve every gate with the walkthrough-assigned owner."""
    return _approve(gate, _GATE_OWNERS.get(gate.checkpoint, "operator"))


def auto_approver(gate: GateContext) -> ApprovalDecision:
    """Approve every gate with a generic operator (used by the simplest demos)."""
    return _approve(gate, "operator")


def rejecting_approver(reject_checkpoint: str, *, approver_id: str = "operator"):
    """Return an approver that rejects one checkpoint and approves the rest."""

    def approver(gate: GateContext) -> ApprovalDecision:
        if gate.checkpoint == reject_checkpoint:
            return ApprovalDecision(
                approver_id=approver_id, decision="reject", comment="rejected by policy"
            )
        return _approve(gate, _GATE_OWNERS.get(gate.checkpoint, approver_id))

    return approver
