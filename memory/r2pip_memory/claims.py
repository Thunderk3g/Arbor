"""B.4 grounded progress claims: every claim must cite a tool-ledger entry.

The prompt discourages fabrication; this verifier makes it non-viable. A claim
is grounded only when it cites an existing ledger entry whose call succeeded.
"""

from r2pip_memory.models import TaskMemory, ToolLedgerEntry

_HASH_PREFIX_LEN = 8


def validate_claims(task_memory: TaskMemory) -> list[str]:
    """Return B.4 violations; an empty list means every claim is grounded."""
    ledger: dict[str, ToolLedgerEntry] = {
        entry.ledger_id: entry for entry in task_memory.tool_ledger
    }
    violations: list[str] = []
    for claim in task_memory.claims:
        if not claim.evidence_ledger_id:
            violations.append(f"claim missing evidence_ledger_id: {claim.text!r}")
            continue
        entry = ledger.get(claim.evidence_ledger_id)
        if entry is None:
            violations.append(
                f"claim cites unknown ledger id {claim.evidence_ledger_id!r}: "
                f"{claim.text!r}"
            )
            continue
        if entry.result_status != "ok":
            violations.append(
                f"claim cites failed tool call "
                f"({entry.ledger_id!r}, status={entry.result_status!r}): {claim.text!r}"
            )
    return violations


def summary_for_claims_sheet(task_memory: TaskMemory) -> str:
    """Render the human-reviewable claims sheet (§1.7): each claim with evidence."""
    ledger = {entry.ledger_id: entry for entry in task_memory.tool_ledger}
    lines = [f"Claims sheet for task {task_memory.task_id}"]
    if not task_memory.claims:
        lines.append("(no claims recorded)")
    for claim in task_memory.claims:
        entry = ledger.get(claim.evidence_ledger_id) if claim.evidence_ledger_id else None
        if entry is None:
            evidence = "UNGROUNDED — no valid tool-ledger evidence"
        else:
            evidence = (
                f"evidence: {entry.tool} "
                f"[{entry.params_hash[:_HASH_PREFIX_LEN]}] "
                f"status={entry.result_status}"
            )
        lines.append(f"- {claim.text} ({evidence})")
    return "\n".join(lines)
