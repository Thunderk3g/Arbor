# ADR-003: Temporal as the Deterministic Spine

**Status:** Accepted · 2026-06-10

## Context
Missions span hours-to-days, survive pod crashes, need compensation (undeploy →
unmerge → release leases), and must be replayable for audit. Hand-rolled state machines
over queues were prototyped and rejected: retry/timer/compensation logic dominated the
code and was untestable.

## Decision
All multi-step platform processes (mission, deploy, ingestion, consolidation) are
Temporal workflows. Agents are *activities*: stochastic content inside deterministic
control flow. Stage gates, retries, leases, and compensation live in workflow code.

## Consequences
- (+) Durable execution for free; workflow history doubles as execution evidence.
- (+) Idempotent + compensable stages are forced by the programming model.
- (−) Temporal operational burden (stateful-pool); accepted vs building worse in-house.
- (−) Workflow versioning discipline required for long-running missions across deploys.
- Alternative considered: Argo Workflows (K8s-native) — rejected: weaker signal/query
  semantics for long-lived human-gated waits (H1–H8 can pend for days).
