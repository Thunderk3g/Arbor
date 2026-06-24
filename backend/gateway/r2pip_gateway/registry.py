"""Tool registry: semver'd tool definitions classified into the four families (RFC-001 §3)."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ToolFamily = Literal["perception", "computation", "action", "memory"]
RiskClass = Literal["low", "medium", "high", "destructive"]


class ToolDef(BaseModel):
    """A registered MCP tool. The handler stands in for the domain MCP server endpoint."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    version: str = "1.0"
    family: ToolFamily
    risk_class: RiskClass
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    # Called as handler(args, credential); excluded from serialization.
    handler: Callable[..., Any] = Field(exclude=True)


class ToolRegistry:
    """Name-keyed catalog of tools served behind the gateway."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def list(self) -> List[ToolDef]:
        return list(self._tools.values())
