"""r2pip_memory — short-term memory and prompt assembler for R2P-IP (RFC §4.1).

Components:
- tokens: single source of truth for token estimation.
- models: pydantic v2 data models (segments, tool ledger, claims, task memory).
- store: session memory store with TTL and checkpoint/restore.
- assembler: budgeted, deterministic, taint-aware prompt assembly.
- claims: B.4 grounded-progress-claim validation and claims-sheet rendering.
- consolidation: B.8 lesson store with rationale enforcement and dedup.
"""

from r2pip_memory.tokens import estimate_tokens
from r2pip_memory.models import (
    AssembledPrompt,
    Claim,
    MemorySegment,
    SegmentKind,
    TaskMemory,
    ToolLedgerEntry,
)
from r2pip_memory.store import SessionMemoryStore
from r2pip_memory.assembler import PromptAssembler
from r2pip_memory.claims import summary_for_claims_sheet, validate_claims
from r2pip_memory.consolidation import LessonRecord, LessonStore

__all__ = [
    "AssembledPrompt",
    "Claim",
    "LessonRecord",
    "LessonStore",
    "MemorySegment",
    "PromptAssembler",
    "SegmentKind",
    "SessionMemoryStore",
    "TaskMemory",
    "ToolLedgerEntry",
    "estimate_tokens",
    "summary_for_claims_sheet",
    "validate_claims",
]
