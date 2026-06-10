# Phase 13 (Appendix A) — Implementation Checklists

> RFC-001 · Appendix A · Status: Draft
> Build-order checklists for the MVP (Phase 1) and the hardening passes that follow.
> Each item is sized for ≤ 1 engineer-week unless marked ◆ (epic). Check = merged + tested + observable.

## A.1 Foundation (weeks 1–4)

- [ ] Monorepo scaffold per §11.1 (Turborepo, Go/Rust/Python/TS toolchains, CODEOWNERS)
- [ ] Terraform `envs/dev`: VPC, GKE (core/agent/sandbox pools), Cloud SQL, Memorystore, GCS buckets
- [ ] Workload identity + Auth0 OIDC wiring; RBAC roles seeded (§7.4)
- [ ] Vault + KMS; secret-zero bootstrap documented
- [ ] Temporal deployed (stateful-pool); hello-world mission workflow
- [ ] NATS JetStream + Kafka (Strimzi) up; topic/stream naming convention ADR
- [ ] OTel collector → Datadog; trace baggage convention (`mission_id`/`task_id`/`agent_id`)
- [ ] CI skeleton: target selection, lint/unit, image build + cosign signing, Argo CD dev sync

## A.2 Audit & Approval Spine (weeks 3–6) — *before any agent runs*

- [ ] Audit Service: append API, per-tenant sequence, hash chain, verify endpoint (§7.7)
- [ ] Hourly WORM sealing to GCS bucket-lock; chain-verification cron + alert
- [ ] Approval Service: request/decide/verify; signed single-use tokens bound to params hash (§7.3)
- [ ] Typed-consequence flow for destructive class
- [ ] Approval inbox UI (minimal): list, evidence panel, approve/reject
- [ ] Policy engine: OPA sidecar, base Rego pack (tool families, destructive deny-by-default), policy-version audit events

## A.3 MCP Gateway & Tool Plane (weeks 4–8)

- [ ] Gateway (Go): schema validation, OPA call, quota, audit emit — the 8-step pipeline (§3.3)
- [ ] Credential injection (15-min scoped tokens); zero secrets in agent/sandbox images
- [ ] Perception: `research.search` (hybrid), `research.fetch`, `repo.read`, `telemetry.query` (Datadog)
- [ ] Computation: `ast.analyze` (tree-sitter svc), `deps.graph` (SCIP), `code.execute` (gVisor sandbox, snapshot workspaces) ◆
- [ ] Action: `repo.write` (agent branches only), `notify.send`; `deploy.release` stub behind H5
- [ ] Memory: `graph.query/write` (staging tier + provenance enforcement), `vector.search/upsert`, `memory.session.*`
- [ ] Taint propagation: ingestion tag → focal rendering → per-turn toolset downgrade (§7.6) ◆

## A.4 Knowledge Plane (weeks 5–10)

- [ ] Ontology v1 as code + migration tool (§4.2)
- [ ] Connectors: arXiv, GitHub, one market feed; Kafka → BigQuery landing
- [ ] Parse/chunk/embed pipeline (Temporal); embeddings → Pinecone (MVP namespaces)
- [ ] Entity + relation extraction with constrained decoding; provenance blocks mandatory
- [ ] Entity resolution v1 (blocking + adjudication; `SAME_AS?` curation queue)
- [ ] Neo4j Aura: staging/trusted tiers, promotion job (corroboration rule)
- [ ] Focal engine v1: seed → PPR → linear scoring → Steiner prune → render + coverage note (§4.4) ◆
- [ ] Focal-graph cache (Redis, keyed query+graph-version)
- [ ] Eval harness: extraction F1, focal-vs-RAG synthesis benchmark (gates from P0 carried into CI)

## A.5 Agent Plane (weeks 8–14)

- [ ] Agent runtime: lifecycle states, checkpointing, budget governor, fresh-context retry (§2.3)
- [ ] Prompt assembler: segmented budgets, prompt hashing → audit
- [ ] PO-Agent: opportunity → PR/FAQ → ARS (`spec.validate`)
- [ ] Head Engineer: decompose → DAG → `blast.analyze` → risk score; direct assignment (star topology, MVP)
- [ ] Developer Agent: implement-in-sandbox loop, self-review checklist, claims sheet
- [ ] QA Agent: `test.generate`, validation report, dissent filing (ACP envelope v1)
- [ ] Mission workflow: stages 1–10 wired with gates H1–H4 (§5)
- [ ] Claims-sheet mechanical verification vs blast radius (auto-reject on scope excess)

## A.6 Delivery & Monitoring (weeks 12–16)

- [ ] Argo Rollouts canary + analysis templates; `deploy.release` live behind H5
- [ ] `deploy.rollback` pre-authorized path + soak-period detectors (stage 12)
- [ ] Infra Agent v1: release + rollback only (no `infra.apply` in MVP)
- [ ] Golden-mission e2e test in CI (staging): corpus → deployed demo service ◆
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
