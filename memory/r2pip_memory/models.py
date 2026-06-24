"""Pydantic v2 models for short-term memory (RFC §4.1)."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

SegmentKind = Literal["system", "ars", "focal", "exemplars", "task_memory", "tool_results"]

Taint = Literal["trusted", "external_untrusted"]

ResultStatus = Literal["ok", "denied", "error"]


class MemorySegment(BaseModel):
    """One candidate piece of an assembled prompt."""

    kind: SegmentKind
    content: str
    relevance: float = 0.5
    created_seq: int  # monotonic recency proxy
    taint: Taint = "trusted"


class ToolLedgerEntry(BaseModel):
    """One audited tool call in task memory (B.4 evidence unit)."""

    ledger_id: str
    tool: str
    params_hash: str
    result_status: ResultStatus
    summary: str = ""
    seq: int


class Claim(BaseModel):
    """A progress claim; must cite a tool-ledger entry to be grounded (B.4)."""

    text: str
    evidence_ledger_id: Optional[str] = None


class TaskMemory(BaseModel):
    """Structured scratchpad: hypotheses, attempts, tool ledger, claims (§4.1)."""

    task_id: str
    hypotheses: list[str] = Field(default_factory=list)
    attempts: list[str] = Field(default_factory=list)
    tool_ledger: list[ToolLedgerEntry] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)


class AssembledPrompt(BaseModel):
    """The output of PromptAssembler.assemble — content-hashed and auditable."""

    text: str
    prompt_hash: str
    included: list[str]  # segment descriptors, e.g. "focal[0]"
    evicted: list[str]  # descriptors with reason, e.g. "focal[2]: over_kind_budget"
    token_estimate: int
