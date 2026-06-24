"""Concrete tool plane: register all four families behind the gateway.

``build_registry`` is the assembly point. Perception/computation/memory tools
are deterministic stand-ins for the real MCP servers; action tools mutate only
in-memory state. The point of the demo is not the handlers — it is that every
call goes through the gateway's policy, taint, approval, budget, and audit
machinery (RFC-001 §3.3).
"""

from __future__ import annotations

from r2pip_focal import InMemoryKnowledgeGraph
from r2pip_gateway import ToolRegistry
from r2pip_ontology import Ontology

from r2pip_platform.tools.action import build_action_tools
from r2pip_platform.tools.computation import build_computation_tools
from r2pip_platform.tools.memory import build_memory_tools
from r2pip_platform.tools.perception import build_perception_tools


def build_registry(graph: InMemoryKnowledgeGraph, ontology: Ontology) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in build_perception_tools():
        registry.register(tool)
    for tool in build_computation_tools():
        registry.register(tool)
    for tool in build_action_tools():
        registry.register(tool)
    for tool in build_memory_tools(graph, ontology):
        registry.register(tool)
    return registry


__all__ = ["build_registry"]
