"""Shared helpers for r2pip_memory tests (not a conftest — imported explicitly)."""

from r2pip_memory.models import Claim, MemorySegment, TaskMemory, ToolLedgerEntry


def seg(kind, content, relevance=0.5, created_seq=0, taint="trusted"):
    return MemorySegment(
        kind=kind,
        content=content,
        relevance=relevance,
        created_seq=created_seq,
        taint=taint,
    )


def block(char: str, tokens: int) -> str:
    """Content whose estimate_tokens cost is exactly ``tokens`` (4 chars/token)."""
    return char * (tokens * 4)


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def ledger_entry(ledger_id, tool="vector.search", params_hash="abcdef1234567890",
                 result_status="ok", summary="", seq=1):
    return ToolLedgerEntry(
        ledger_id=ledger_id,
        tool=tool,
        params_hash=params_hash,
        result_status=result_status,
        summary=summary,
        seq=seq,
    )


def task_memory(task_id="task-1", tool_ledger=None, claims=None):
    return TaskMemory(
        task_id=task_id,
        tool_ledger=tool_ledger or [],
        claims=claims or [],
    )


def claim(text, evidence_ledger_id=None):
    return Claim(text=text, evidence_ledger_id=evidence_ledger_id)
