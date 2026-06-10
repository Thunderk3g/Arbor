# ADR-004: Single MCP Gateway Choke Point

**Status:** Accepted · 2026-06-10

## Context
Constraints require: every tool call logged, policy-checked, quota'd; agents must never
hold long-lived credentials; prompt-injection damage must be cappable per call. If
agents can reach domain services directly, each service must reimplement all of this.

## Decision
One MCP gateway (Go) is the only network path from agents to anything. Pipeline per
call: schema validation → OPA → quota/budget → taint check → scoped 15-min credential
injection → execute → result taint-tagging → hash-chained audit event. Domain MCP
servers sit behind it and trust only gateway identity.

## Consequences
- (+) Security/audit invariants enforced in exactly one place; new tools inherit them.
- (+) The tool firewall (ADR-008) is implementable as a gateway concern.
- (−) Gateway is on every hot path → must be horizontally trivial (stateless Go, p99 budget 10 ms overhead) and is the most load-tested component.
- (−) Single choke point = single outage point → multi-replica, PDB, and a read-only "perception degraded mode" if policy backend is unavailable (Action calls fail closed).
