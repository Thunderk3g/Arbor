# ADR-005: MCP / A2A / ACP Protocol Split

**Status:** Accepted · 2026-06-10

## Context
Three interaction shapes exist: agent↔world (data/side effects), agent↔agent discovery
and delegation, agent↔agent rich conversation. Forcing all three through one protocol
either bloats MCP into a messaging bus or turns agent chat into untyped tool calls.

## Decision
- **MCP** for everything that is not another agent (tools, resources). Never agent-to-agent.
- **A2A** for capability discovery (Agent Cards) and task delegation with artifacts — contract-net bidding, cross-cell handoffs, future cross-org federation.
- **ACP** for conversational peer threads within an established collaboration (reviews, dissent, clarification) — REST-native multipart suits diff+claims payloads.

All three ride NATS JetStream internally as envelope formats so the audit plane taps a
single durable, replayable stream.

## Consequences
- (+) Each protocol stays idiomatic; one audit tap covers all coordination.
- (+) Federation path (Enterprise) reuses A2A as designed by its ecosystem.
- (−) Two agent-to-agent envelope formats to maintain → shared envelope library in `agents/protocols/`.
- Watch item (OQ-3): A2A spec maturity; abstraction layer keeps us swappable.
