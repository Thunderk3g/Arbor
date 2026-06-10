# Phase 5 — Autonomous Software Engineering Workflow

> RFC-001 · Section 5 · Status: Draft

The engineering loop is a **deterministic Temporal workflow** whose activities invoke
stochastic agents. The workflow owns ordering, retries, gates, and audit; agents own
content. Thirteen stages:

## 5.1 Stage Definitions

| # | Stage | Owner | Gate to proceed |
|---|---|---|---|
| 1 | **Agent-Ready Specification (ARS)** | PO-Agent | Human approval (intent), `spec.validate` pass |
| 2 | **AST analysis** | Head Engineer | Parse coverage ≥ 99% of target repos |
| 3 | **Semantic indexing** | Platform (auto) | Symbol embeddings fresh (≤ 1 commit stale) |
| 4 | **Dependency graphing** | Platform (auto) | SCIP index complete; ownership map resolved |
| 5 | **Task decomposition** | Head Engineer | DAG acyclic; every task has acceptance criteria + ≤ 1-day scope |
| 6 | **Blast radius analysis** | Head Engineer | Every task annotated: affected symbols/services/tests/data; risk score R computed |
| 7 | **Execution planning** | Head Engineer | Plan artifact: order, parallelism, integration branch strategy, rollback plan. HITL if R ≥ 0.5 |
| 8 | **Code generation** | Developer Agents | Self-review checklist + claims sheet emitted |
| 9 | **Testing** | QA Agents | Unit+integration green; mutation score ≥ baseline; new code coverage ≥ 80% |
| 10 | **Validation** | QA + platform | Claims sheet mechanically verified vs blast radius; security scan; license scan; dissents resolved |
| 11 | **Deployment** | Infra Agent | HITL approval token (mode-dependent); canary analysis green |
| 12 | **Monitoring** | Infra Agent | SLO baseline registered; anomaly detectors armed (24h soak) |
| 13 | **Autonomous evolution** | BI/PO/Head Eng | Telemetry-vs-intent deltas spawn new Opportunities (loop closure) |

### ARS schema (stage 1 contract)

```yaml
ars_id: ARS-142
intent: one-paragraph product intent (human-approved verbatim)
provenance: [paper_ids, signal_ids, opportunity_id]
functional_requirements:        # testable, numbered
  - FR1: "..."
acceptance_criteria:            # machine-checkable where possible
  - AC1: {kind: test, description: "...", verification: "integration test"}
non_goals: ["..."]              # blast-radius ceiling: agents may not exceed
constraints: {stack: ..., budgets: {tokens: ..., infra_usd: ...}, deadlines: ...}
risk_notes: data sensitivity, one-way doors anticipated
retry_policy: {max_attempts: 3, escalation: human_architect}
```

## 5.2 Sequence Diagram (stages 5–12)

```mermaid
sequenceDiagram
    autonumber
    participant T as Temporal Mission WF
    participant HE as Head Engineer
    participant CI as Code Intelligence svc
    participant DEV as Dev Agents
    participant QA as QA Agents
    participant POL as Policy/Approval
    participant INF as Infra Agent
    participant OBS as Observability

    T->>HE: activity: decompose(ARS-142)
    HE->>CI: ast.analyze + deps.graph + blast.analyze
    CI-->>HE: code graph + impact sets
    HE-->>T: Task DAG + risk scores
    T->>POL: gate: plan approval (R=0.34 → supervised)
    POL-->>T: token granted (human approved plan)
    par parallel tracks per DAG
        T->>DEV: activity: implement(T3) [lease]
        DEV->>DEV: codegen in sandbox, self-review
        DEV-->>T: diff + claims sheet
        T->>QA: activity: validate(T3)
        QA-->>T: ValidationReport
    end
    T->>T: integrate branch, re-run full suite
    T->>POL: gate: deploy approval token
    POL-->>T: token (operator approved)
    T->>INF: activity: deploy.release(canary)
    INF->>OBS: register baseline + abort thresholds
    loop canary steps 5→25→50→100
        OBS-->>INF: analysis verdict
        alt metrics breach
            INF->>INF: deploy.rollback (pre-authorized)
            INF-->>T: FAILED(rollback complete) → escalate
        end
    end
    INF-->>T: deployed; 24h soak armed
```

## 5.3 Blast Radius Analysis

`blast.analyze(diff | planned-change)` returns:

- **Symbol impact set:** reverse closure over call/import graph from touched symbols.
- **Service impact set:** symbols → owning services (ownership map) → runtime dependents (service mesh topology).
- **Test impact set:** tests covering the impact set (coverage index) — drives targeted test selection *and* flags untested impact (which inflates R).
- **Data impact:** migrations / schema-touching changes auto-classified one-way-door.
- **Risk score:** `R = w₁·|services| + w₂·untested_fraction + w₃·data_sensitivity + w₄·novelty(task-class)` normalized to [0,1]; weights calibrated against historical defect escapes (recomputed weekly, §1.7).

Hard rule: a task whose realized diff exceeds its declared blast radius is **auto-rejected**
at validation — agents cannot silently widen scope.

## 5.4 Rollback & Recovery Strategies

| Layer | Mechanism | RTO target |
|---|---|---|
| Code | Revert commit on protected branch (every merge is revertable; no force-push) | minutes |
| Deploy | Argo Rollouts abort → previous ReplicaSet still warm (blue/green or canary) | < 60 s |
| Schema | Expand–migrate–contract only; contract step gated 1 release behind; reversible migration scripts mandatory | minutes |
| Data | Pre-change snapshot for any Action tool touching data (automatic, policy-enforced); PITR on Postgres; BigQuery time-travel | minutes–hours |
| Graph | Staging tier never auto-promotes on failure; tier demotion + provenance-based purge for poisoned sources | hours |
| Mission | Temporal: every stage idempotent + compensable; failed mission compensates in reverse order (undeploy → unmerge → release leases) | automatic |

**Recovery doctrine:** roll *back* first, diagnose second, roll *forward* only with a
new validated revision. Infra Agent is pre-authorized for rollback (reversible) but
never for the subsequent re-deploy (requires fresh approval token).

## 5.5 Human Intervention Points

| Point | Trigger | Human role | UI (§8) |
|---|---|---|---|
| H1 | Opportunity → ARS | Strategist approves intent/PR-FAQ | Opportunity inbox |
| H2 | Execution plan, R ≥ 0.5 | Architect approves plan + blast radius | Architecture review |
| H3 | Merge, R ≥ autonomy threshold | Architect reviews claims sheet (+diff if collaborative mode) | Code explorer |
| H4 | Any one-way door (delete, schema contract, external publish, spend > budget) | Typed-consequence confirmation | Approval inbox |
| H5 | Deploy to production | Operator grants approval token | Execution dashboard |
| H6 | Canary auto-rollback fired | Operator owns incident; swarm paused for service | Execution dashboard |
| H7 | Dissent unresolved by Head Engineer | Architect arbitrates | Review thread |
| H8 | Sampled post-hoc audit (≥5% of autonomous merges) | Architect spot-checks | Audit explorer |

Stage 13 (autonomous evolution) generates *proposals only* — evolution work re-enters
at stage 1 with full gating. Autonomy compounds through faster loops, never through
skipped gates.

---

*Next: [Section 6 — Infrastructure](06-infrastructure.md)*
