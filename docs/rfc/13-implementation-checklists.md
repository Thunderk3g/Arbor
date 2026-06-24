# Phase 13 (Appendix A) — Implementation Checklists

> RFC-001 · Appendix A · Status: Draft
> Build-order checklists for the MVP (Phase 1) and the hardening passes that follow.
> Each item is sized for ≤ 1 engineer-week unless marked ◆ (epic). Check = merged + tested + observable.

> **What a tick means here (2026-06):** a checked box marks a **tested Python reference
> implementation merged** (per [ADR-011](../adr/011-python-reference-implementations.md)) whose
> behavior is pinned by a pytest suite — *not* production infrastructure deployed. The infra
> items (Terraform, GKE, Temporal, Neo4j, Kafka, Argo, Datadog, OPA sidecar, Vault) remain
> unticked because they are not built. Partially-delivered items stay unticked with a
> parenthetical noting what exists vs. what is pending. See
> [Appendix C — Reference-Implementation Status](15-reference-implementation-status.md) for the
> full map of section → package → tests.

## A.1 Foundation (weeks 1–4)

- [ ] Monorepo scaffold per §11.1 (Turborepo, Go/Rust/Python/TS toolchains, CODEOWNERS) (reference impl: Python package roots `backend/`, `graph/`, `memory/`, `platform/` with pytest suites and `scripts/run_demo.py`; Turborepo / Go·Rust·TS toolchains / CODEOWNERS pending)
- [ ] Terraform `envs/dev`: VPC, GKE (core/agent/sandbox pools), Cloud SQL, Memorystore, GCS buckets
- [ ] Workload identity + Auth0 OIDC wiring; RBAC roles seeded (§7.4)
- [ ] Vault + KMS; secret-zero bootstrap documented
- [ ] Temporal deployed (stateful-pool); hello-world mission workflow
- [ ] NATS JetStream + Kafka (Strimzi) up; topic/stream naming convention ADR
- [ ] OTel collector → Datadog; trace baggage convention (`mission_id`/`task_id`/`agent_id`)
- [ ] CI skeleton: target selection, lint/unit, image build + cosign signing, Argo CD dev sync

## A.2 Audit & Approval Spine (weeks 3–6) — *before any agent runs*

- [x] Audit Service: append API, per-tenant sequence, hash chain, verify endpoint (§7.7) (reference impl: `r2pip_audit` — `InMemoryAuditStore`, `verify_chain`, Merkle segment roots, FastAPI verify endpoint)
- [ ] Hourly WORM sealing to GCS bucket-lock; chain-verification cron + alert (reference impl: in-process `verify_chain` + `segment_merkle_root`; GCS bucket-lock WORM and cron/alert pending)
- [x] Approval Service: request/decide/verify; signed single-use tokens bound to params hash (§7.3) (reference impl: `r2pip_approval` — Ed25519 single-use tokens, params-hash binding, TTL, replay rejection)
- [x] Typed-consequence flow for destructive class (reference impl: `r2pip_approval` typed-consequence + dual-control enforcement)
- [ ] Approval inbox UI (minimal): list, evidence panel, approve/reject (reference impl: programmatic approver callback `scripted_approver(GateContext)`; web inbox UI pending)
- [ ] Policy engine: OPA sidecar, base Rego pack (tool families, destructive deny-by-default), policy-version audit events (reference impl: ordered in-process `PolicyEngine` in `r2pip_gateway` with deny-by-default Action rules and per-invoke `policy_decision` audit events; OPA sidecar + Rego pack pending)

## A.3 MCP Gateway & Tool Plane (weeks 4–8)

- [x] Gateway (Go): schema validation, OPA call, quota, audit emit — the 8-step pipeline (§3.3) (reference impl: `r2pip_gateway` `Gateway.invoke` — schema validation, ordered policy engine, budget/quota, one audit event per invoke; **Python** not Go, in-process policy not OPA, per ADR-011)
- [ ] Credential injection (15-min scoped tokens); zero secrets in agent/sandbox images (reference impl: pipeline credential-injection step present but issues a placeholder scoped token; real Vault/KMS-backed 15-min tokens pending)
- [ ] Perception: `research.search` (hybrid), `research.fetch`, `repo.read`, `telemetry.query` (Datadog) (reference impl: deterministic `research.search`/`research.fetch`/`repo.read` stand-ins behind the gateway, results tagged `external_untrusted`; hybrid retrieval, `telemetry.query`/Datadog pending)
- [ ] Computation: `ast.analyze` (tree-sitter svc), `deps.graph` (SCIP), `code.execute` (gVisor sandbox, snapshot workspaces) ◆ (reference impl: deterministic `ast.analyze`/`deps.graph`/`blast.analyze`/`code.execute`/`spec.validate`/`test.generate` stand-ins; tree-sitter/SCIP/gVisor sandbox pending)
- [ ] Action: `repo.write` (agent branches only), `notify.send`; `deploy.release` stub behind H5 (reference impl: in-memory `repo.write`/`repo.merge`/`notify.send`/`deploy.release`/`deploy.rollback`; `deploy.release` requires a valid H5 approval token bound to params hash; real VCS/deploy backends pending)
- [ ] Memory: `graph.query/write` (staging tier + provenance enforcement), `vector.search/upsert`, `memory.session.*` (reference impl: `graph.write`/`graph.query`/`focal.extract` with mandatory-provenance and staging-tier enforcement, plus `memory.session.*` via `r2pip_memory` `SessionMemoryStore`; `vector.search/upsert` pending)
- [x] Taint propagation: ingestion tag → focal rendering → per-turn toolset downgrade (§7.6) ◆ (reference impl: ADR-008 taint firewall in `r2pip_gateway` — evaluated *before* the approval gate — plus staging-tier exclusion / brief-taint in `r2pip_focal` and untrusted fencing in `r2pip_memory`)

## A.4 Knowledge Plane (weeks 5–10)

- [ ] Ontology v1 as code + migration tool (§4.2) (reference impl: `r2pip_ontology` — 24 node types / 4 layers / 13 relations in `ontology-v1.yaml`, loader + `validate_mutation_batch` with mandatory provenance, Cypher/JSON-Schema export; versioned-migration tool pending)
- [ ] Connectors: arXiv, GitHub, one market feed; Kafka → BigQuery landing (not built; the demo uses the static `r2pip_platform.corpus` seed graph)
- [ ] Parse/chunk/embed pipeline (Temporal); embeddings → Pinecone (MVP namespaces) (not built; corpus carries toy deterministic embeddings for focal cosine scoring only)
- [ ] Entity + relation extraction with constrained decoding; provenance blocks mandatory (not built as a pipeline; provenance blocks *are* mandatory and enforced on `graph.write` via `r2pip_ontology`)
- [ ] Entity resolution v1 (blocking + adjudication; `SAME_AS?` curation queue) (not built; `SAME_AS_CANDIDATE` relation defined in the ontology but no ER/adjudication pipeline)
- [ ] Neo4j Aura: staging/trusted tiers, promotion job (corroboration rule) (reference impl: staging/trusted tier model with staging-exclusion enforced in `r2pip_focal`/`r2pip_ontology`; Neo4j Aura backend and promotion job pending — graph is in-memory)
- [x] Focal engine v1: seed → PPR → linear scoring → Steiner prune → render + coverage note (§4.4) ◆ (reference impl: `r2pip_focal` `focal_extract` — ACL/PPR-push, 5 purpose profiles, linear scoring, hop-bounded prune, render + `why_included`/`coverage_note`, staging-tier exclusion)
- [ ] Focal-graph cache (Redis, keyed query+graph-version) (not built; focal extraction is recomputed per call)
- [ ] Eval harness: extraction F1, focal-vs-RAG synthesis benchmark (gates from P0 carried into CI) (not built)

## A.5 Agent Plane (weeks 8–14)

- [x] Agent runtime: lifecycle states, checkpointing, budget governor, fresh-context retry (§2.3) (reference impl: `r2pip_platform.agents.AgentRuntime` — per-turn prompt build, gateway-mediated tool ledger, `fresh_context` retry; budget governor in `r2pip_gateway`; checkpoint/restore via `r2pip_memory` `SessionMemoryStore`)
- [x] Prompt assembler: segmented budgets, prompt hashing → audit (reference impl: `r2pip_memory` `PromptAssembler` — segmented budgets + deterministic eviction + untrusted fencing; every turn's `prompt_hash` written as a `prompt` audit event by `AgentRuntime`)
- [x] PO-Agent: opportunity → PR/FAQ → ARS (`spec.validate`) (reference impl: `POAgent.draft_spec` — focal `spec_drafting` brief → ARS-142 → `spec.validate` → `graph.write`)
- [x] Head Engineer: decompose → DAG → `blast.analyze` → risk score; direct assignment (star topology, MVP) (reference impl: `HeadEngineer.plan` — `ast.analyze`/`deps.graph`/`blast.analyze` → `compute_risk_score` → autonomy mode + task DAG; direct assignment)
- [x] Developer Agent: implement-in-sandbox loop, self-review checklist, claims sheet (reference impl: `DeveloperAgent.build` — tainted study turn (firewalled `repo.write`) + sandbox `code.execute` + clean-context commit turn; emits a grounded claims sheet)
- [x] QA Agent: `test.generate`, validation report, dissent filing (ACP envelope v1) (reference impl: `QAAgent.validate` — `test.generate`, mutation-score vs baseline gate, dissent record; ACP envelope is an informal dict, not a wire protocol)
- [x] Mission workflow: stages 1–10 wired with gates H1–H4 (§5) (reference impl: `MissionOrchestrator` — Temporal-workflow stand-in driving stages 0–13 with real Approval-Service gates H1/H2/H4 (and H5); a rejected gate aborts the mission)
- [x] Claims-sheet mechanical verification vs blast radius (auto-reject on scope excess) (reference impl: `MissionOrchestrator._verify_claims_sheet` — aborts on `symbols_touched` over blast radius or billing-touch (ARS non-goal), plus `validate_claims` grounding check)

## A.6 Delivery & Monitoring (weeks 12–16)

- [ ] Argo Rollouts canary + analysis templates; `deploy.release` live behind H5 (reference impl: `deploy.release` gated by an H5 approval token bound to the image-digest params hash, verified at the gateway; Argo Rollouts canary/analysis templates pending)
- [ ] `deploy.rollback` pre-authorized path + soak-period detectors (stage 12) (reference impl: `deploy.rollback` registered as a pre-authorized (no-approval) Action tool; soak-period detectors pending)
- [ ] Infra Agent v1: release + rollback only (no `infra.apply` in MVP) (reference impl: `InfraAgent.deploy` performs release only and is role-scoped to deploy tools; no `infra.apply`)
- [ ] Golden-mission e2e test in CI (staging): corpus → deployed demo service ◆ (reference impl: golden mission MSN-4413 runs end-to-end as a pytest e2e + `scripts/run_demo.py`/`python -m r2pip_platform`; CI-on-staging against a real deployed service pending)
- [ ] Dashboards: mission funnel, $/merged-change, validation pass rate, reviewer catch-rate
- [ ] **MVP exit gate (§12): first fully-audited mission < 5 days wall-clock**

## A.7 Post-MVP Hardening (Phase 2+ entry criteria)

- [ ] Contract-net bidding + leases replace direct assignment (§2.8)
- [ ] A2A agent cards; ACP review threads in UI
- [ ] Episodic consolidation + exemplar service (ICL loop, §4.1)
- [ ] Autonomy calibration job (weekly threshold recompute, §1.7) + red-team seeded-defect sampling
- [ ] Milvus on GKE migration (dual-write window, recall parity check)
- [ ] Firecracker sandbox pool; egress proxy dependency-confusion screening
- [ ] RLS → schema-per-tenant promotion path; graph partition by layer
- [ ] Compliance export pack v1 (SOC 2 evidence from audit stream)

## A.8 Definition of Done (every subsystem)

1. OTel traces + Datadog dashboard + alert policy exist.
2. Audit events emitted for every mutation; chain verified in CI.
3. OPA policy coverage test (allow + deny cases) in repo.
4. Runbook in `docs/runbooks/`; failure modes table filled.
5. Load profile in `tests/load/` meeting the §9.5 capacity anchor share.
