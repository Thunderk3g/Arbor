"""r2pip_gateway — MCP Gateway reference implementation (RFC-001 §3.3, ADR-004, ADR-008)."""

from .budget import BudgetGovernor
from .gateway import Gateway, GatewayResult
from .policy import (
    CallContext,
    PolicyDecision,
    PolicyEngine,
    Principal,
    compute_params_hash,
)
from .registry import ToolDef, ToolRegistry
from .validation import validate_args

__all__ = [
    "BudgetGovernor",
    "CallContext",
    "Gateway",
    "GatewayResult",
    "PolicyDecision",
    "PolicyEngine",
    "Principal",
    "ToolDef",
    "ToolRegistry",
    "compute_params_hash",
    "validate_args",
]
