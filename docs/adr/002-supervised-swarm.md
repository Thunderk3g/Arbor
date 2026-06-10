# ADR-002: Hybrid Supervised Swarm Topology

**Status:** Accepted · 2026-06-10

## Context
Pure central orchestration bottlenecks on one context window and is a single point of
failure. Pure peer-to-peer mesh maximizes parallelism but produces coordination thrash,
emergent deadlock, and an audit nightmare. We need parallel creativity *and*
deterministic accountability.

## Decision
Per-mission cells: a Head Engineer Agent supervises; rosters recruited via contract-net
bidding; peers coordinate via A2A/ACP *within* the cell; everything crossing the cell
boundary (tools, deploys, approvals) goes through Temporal workflows and the MCP
gateway. Shared state lives only in the graph and task memory — agent-to-agent state
sharing outside recorded messages is forbidden.

## Consequences
- (+) Failure containment per cell; supervisor adoption from Temporal state on crash.
- (+) Every coordination act is a recorded message → fully auditable swarm.
- (−) More moving parts than star topology → MVP ships star topology first (ADR-scoped exception), contract-net lands in Phase 2.
- Livelock guard: bid-storm circuit breaker falls back to direct assignment.
