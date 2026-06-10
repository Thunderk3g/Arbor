"""Pydantic models for AuditEvent per RFC-001 §7.7."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Actor(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["human", "agent", "system"]
    id: str
    on_behalf_of_mission: Optional[str] = None


class Action(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal[
        "prompt",
        "tool_call",
        "file_mod",
        "approval",
        "policy_decision",
        "deploy",
        "login",
    ]
    tool: Optional[str] = None
    params_hash: Optional[str] = None
    content_ref: Optional[str] = None


class EventContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    trace_id: Optional[str] = None
    taint: Literal["trusted", "external_untrusted"] = "trusted"


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    seq: int = Field(ge=1)
    tenant_id: str
    actor: Actor
    action: Action
    context: EventContext
    ts: str  # ISO-8601 UTC
    prev_hash: str
    event_hash: str
