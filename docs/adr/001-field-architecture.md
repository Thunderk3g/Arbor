# ADR-001: Data-to-Product Field over Linear Pipeline

**Status:** Accepted · 2026-06-10

## Context
Research-to-product value is latent: cross-domain intersections (paper × market signal ×
telemetry) appear long after ingestion. A linear pipeline fixes information flow
direction and stage boundaries at design time, which structurally prevents discovering
those intersections.

## Decision
Build a persistent knowledge substrate (graph + vectors + warehouse) over which four
asynchronous loops (perception, insight, engineering, evolution) operate. Loops
integrate only through the substrate — no loop calls another directly. A deterministic
Temporal spine runs *inside* the engineering loop only.

## Consequences
- (+) Latent cross-domain discovery becomes a graph query, not a re-architecture.
- (+) Loops degrade independently; ingestion outage doesn't halt engineering.
- (−) Always-on substrate cost; mitigated by tiered storage and MVP corpus limits.
- (−) Reasoning audits need explicit provenance edges — made mandatory (graph.write schema).
- Risk: substrate becomes a junk drawer → trust tiers + ontology-as-code with migrations.
