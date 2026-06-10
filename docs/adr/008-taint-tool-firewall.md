# ADR-008: Taint-Based Tool Firewall for Prompt Injection

**Status:** Accepted · 2026-06-10

## Context
The platform's job is to read attacker-influenceable content (papers, web, READMEs) and
then take actions. Fencing and instruction-hierarchy prompting reduce but cannot
eliminate injection; any defense that depends on the model "behaving" fails the threat
model. The damage cap must be mechanical.

## Decision
Provenance taint (`trusted | external_untrusted`) propagates from ingestion through
graph nodes, focal-graph rendering, into each assembled prompt. The MCP gateway
inspects the taint of the agent's current context per turn: untrusted taint present →
**Action-family tools and trusted-tier graph writes are blocked for that turn**.
Perception/Computation remain available. Egress only via allowlisting proxy.

## Consequences
- (+) Worst-case injected instruction wastes tokens; it cannot merge, deploy, exfiltrate via URL beacons, or poison the trusted tier.
- (−) Workflow friction: acting on researched content requires a *laundering step* — claims must be promoted to trusted tier (corroboration/curation) before an Action-bearing task consumes them. This is accepted as the core safety/velocity trade.
- (−) Taint is coarse (binary, MVP); per-source granular trust scores are a Phase 3 refinement.
- Defense-in-depth retained: fencing, sentinels, output scanning stay — firewall is the backstop, not the only layer.
