# Appendix C — Reference-Implementation Status

> RFC-001 · Appendix C · Status: Living document · Updated 2026-06-25
> A map of which RFC sections / ADRs have a **tested reference implementation merged**, in
> which package, covering which behaviors, with how many tests — and what is deliberately
> stubbed or deferred. This is the companion to
> [Appendix A — Implementation Checklists](13-implementation-checklists.md): Appendix A is the
> build-order; this appendix is the as-built.

## Scope (read this first)

What exists today is a set of **tested Python reference implementations** of the platform's
protocol cores and their composition, per
[ADR-011](../adr/011-python-reference-implementations.md). The pytest suites — not the Python
code — are the behavioral contract: hash-chain semantics, token binding and replay rejection,
the gateway's ordered policy + taint firewall, ontology validation, focal extraction, prompt
assembly, and the end-to-end golden mission. Everything runs **in-memory and in-process**: one
audit chain, one signing key, one knowledge graph per tenant, assembled by a single composition
root (`r2pip_platform.system.build_platform`).

This is **not production infrastructure.** There is no Terraform, GKE, Temporal, Neo4j, Kafka,
Argo, Datadog, OPA sidecar, or Vault; the MCP "tools" are deterministic stand-ins for the real
servers, and the audit appender's throughput is far below the Go §9.5 target (an ADR-011 port
blocker). The value is that the cryptographic, chaining, policy, and orchestration semantics are
**executable specification** that the eventual Go/infra build must reproduce, with golden test
vectors extractable from these suites.

## Status matrix

Seven packages, **219 tests** total. "Tests" counts are approximate (test-function counts as of
2026-06-25).

| RFC § / ADR | Package | Key behaviors covered (reference impl) | Tests | Deliberately stubbed / deferred |
|---|---|---|---|---|
| §7.7 Audit | `backend/audit` (`r2pip_audit`) | Append API, per-tenant monotonic sequence, hash-chain linking, tamper detection, Merkle segment roots, `verify_chain`, FastAPI verify endpoint | ~19 | GCS bucket-lock WORM sealing, hourly seal cron + alert; Go port (ADR-011) for §9.5 throughput |
| §7.3 / ADR-009 Approval | `backend/approval` (`r2pip_approval`) | Ed25519 keypair, request/decide/verify, single-use tokens bound to params hash, TTL, replay rejection, typed-consequence for destructive class, dual-control | ~26 | Approval inbox UI; Go port (ADR-011) |
| §3.3 / ADR-004, ADR-008 Gateway | `backend/gateway` (`r2pip_gateway`) | `invoke` pipeline (schema validation → ordered policy → budget/quota → credential step → execute → result-taint → audit), ordered `PolicyEngine` with taint firewall **before** the approval gate, deny-by-default Action rules, role-scoping, mandatory-provenance memory rule, one audit event per invoke, `compute_params_hash`, full-structure taint-tier scan | ~27 | OPA sidecar + Rego pack; real Vault/KMS 15-min scoped credentials (currently a placeholder token); **Go** port |
| §4.2 Ontology | `graph/ontology` (`r2pip_ontology`) | Ontology-as-code: 24 node types / 4 layers / 13 relations (`ontology-v1.yaml`), loader + structural validation, `validate_mutation_batch` with mandatory provenance and tier/taint alignment, Cypher + JSON-Schema export | ~37 | Versioned migration tool; the package stays Python permanently per ADR-011 |
| §4.4 / ADR-007 Focal Graph | `graph/focal` (`r2pip_focal`) | `focal_extract`: seed → ACL/personalized-PageRank push → linear scoring → hop-bounded prune → render with `why_included` + `coverage_note`; 5 purpose profiles (`opportunity_mining`, `code_task_brief`, `spec_drafting`, `review`, `explain`); staging-tier exclusion by default; brief-taint downgrade on opt-in to staging | ~30 | Redis focal cache (keyed query+graph-version); Neo4j Aura backend (graph is in-memory) |
| §4.1, §7.6, App. B Memory | `memory` (`r2pip_memory`) | `PromptAssembler` (segmented budgets, deterministic eviction, untrusted fencing), tool ledger, `validate_claims` grounded-claim check (B.4), `summary_for_claims_sheet`, lesson consolidation with rationale enforcement (`LessonStore`), `SessionMemoryStore` checkpoint/restore | ~36 | Pinecone/Milvus vector backends; episodic exemplar/ICL service (§4.1) |
| §2, §5, §10 Platform | `platform` (`r2pip_platform`) | Composition root wiring all six slices; 17 tool handlers across 4 families (perception/computation/action/memory); `AgentRuntime`; BI / PO / HeadEngineer / Developer / QA / Infra role agents + risk scoring; `MissionOrchestrator` (stages 0–13, gates H1/H2/H4/H5, claims-sheet-vs-blast-radius check, audit-chain finalization); FastAPI `app.py`; `demo.py` | ~44 | Temporal workflow engine (orchestrator is the stand-in); contract-net bidding (direct assignment only); A2A/ACP wire protocols (ACP envelope is an informal dict) |

### What the composition demonstrates (golden mission MSN-4413)

The platform package composes the six slices into the
[golden-mission walkthrough](../../examples/mission-walkthrough.md), run end-to-end and asserted
by the platform suite:

- **Insight → spec → plan → build → merge → deploy**, each human gate routed through the real
  Approval Service; a rejected gate aborts the mission.
- **Taint firewall set-piece:** the Developer's first turn ingests an untrusted paper and an
  attempted `repo.write` is blocked by the gateway (ADR-008) *before* any approval is consulted;
  a fresh clean-context turn commits the sandbox-validated artifact.
- **Staging-tier poison defense:** the corpus seeds a staging-tier injection paper; the focal
  engine excludes it by default and records it in the `coverage_note`.
- **H5 deploy binding:** `deploy.release` requires a single-use token bound to the image-digest
  params hash, verified at the gateway.
- **Forensics:** after completion the orchestrator verifies the audit chain and answers the four
  walkthrough questions ("why does this feature exist / who approved production / could the paper
  have injected anything / reproduce it") from the hash-chained event log.

## How to run it

From the repo root:

```bash
# Full reference-implementation test suite (the behavioral contract — 219 tests)
pytest

# Golden mission MSN-4413, human-readable trace, no install required
python scripts/run_demo.py
# (equivalently, with the packages importable: python -m r2pip_platform)

# FastAPI surface: GET /health, GET /tools, POST /missions/run, GET /audit/verify
uvicorn r2pip_platform.app:app
```

`scripts/run_demo.py` puts the six slice roots plus the platform root on `sys.path`, so no
packaging step is needed.

## Deliberately deferred (and why)

Per ADR-011, the protocol cores ship as Python reference implementations now because correctness
matters more than the host language and "everything merged must have run its tests." The
following are **knowingly out of scope** for this stage and tracked in Appendix A:

- **Production infrastructure** — Terraform/GKE/Vault/Temporal/Kafka/Neo4j/Pinecone/Argo/Datadog.
  The in-memory stores and deterministic tool stand-ins exist so the *semantics* are testable
  without standing up the cluster.
- **Go ports of audit + approval + gateway** — the §11 language table calls for Go; ADR-011 is the
  tracking record, with golden test vectors to be extracted from these suites at port time. The
  Python audit appender is below the §9.5 throughput anchor (a flagged port blocker).
- **OPA sidecar / Rego** — policy is enforced today by an ordered in-process `PolicyEngine`; the
  ordering guarantees (taint firewall before approval gate) and deny-by-default behavior are the
  contract the Rego pack must satisfy.
- **Real ingestion + extraction + ER + eval harness, vector search, focal cache, and the
  HITL/observability surfaces** (approval inbox UI, dashboards, OTel→Datadog) — not built.
