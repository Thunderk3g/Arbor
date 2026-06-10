# Phase 10 — API Specifications

> RFC-001 · Section 10 · Status: Draft
> Conventions: external + UI = REST/OpenAPI 3.1 via the BFF; service-to-service = gRPC (proto3) with OTel interceptors; all calls carry `tenant_id` (from auth), `trace_id`, idempotency keys on mutations. Errors: RFC 9457 problem+json. Pagination: cursor-based. AuthZ: OPA via gateway middleware.

## 10.1 Service Map

| Service | Style | Consumers |
|---|---|---|
| Agent Service | gRPC + REST admin | Temporal activities, UI |
| Knowledge Graph Service | gRPC (+ GraphQL read for UI) | Agents (via MCP), UI |
| Memory Service | gRPC | Agent runtimes |
| GraphRAG Service | gRPC | MCP gateway (`focal.extract`, `graph.community`) |
| Planning Service | gRPC | Mission workflows |
| Execution Service | gRPC | Workflows, sandbox controller |
| Research Service | REST + gRPC | Ingestion workers, UI |
| Infrastructure Service | gRPC | Infra Agent (gated), tenant provisioner |
| Audit Service | gRPC write / REST read | Everything (write); compliance UI (read) |
| Approval Service | REST + gRPC | UI/chat-ops (decide), gateway (verify) |

## 10.2 Representative Specs

### Agent Service (gRPC)

```protobuf
syntax = "proto3";
package r2pip.agent.v1;

service AgentService {
  rpc SpawnAgent(SpawnAgentRequest) returns (AgentInstance);
  rpc GetAgent(GetAgentRequest) returns (AgentInstance);
  rpc ListAgents(ListAgentsRequest) returns (ListAgentsResponse);
  rpc SendDirective(SendDirectiveRequest) returns (DirectiveAck); // pause|resume|abort|reprioritize
  rpc StreamEvents(StreamEventsRequest) returns (stream AgentEvent); // UI timeline feed
}

message SpawnAgentRequest {
  string mission_id = 1;
  string agent_type = 2;        // po|bi|head_engineer|developer|qa|infra
  string brief_ref = 3;         // focal graph + task memory bundle
  Budget budget = 4;            // tokens, cpu_seconds, wallclock, usd
  string idempotency_key = 5;
}
message AgentInstance {
  string id = 1;
  string state = 2;             // per §2.3 lifecycle
  string checkpoint_ref = 3;
  Budget budget_remaining = 4;
}
```

### GraphRAG Service — `POST /v1/focal-graphs` (REST mirror)

Request:
```json
{
  "query": "Which recent battery-electrolyte methods intersect unmet needs in grid storage?",
  "purpose": "opportunity_mining",
  "domains": ["research", "market"],
  "max_nodes": 120,
  "token_budget": 6000
}
```
Response `201`:
```json
{
  "focal_graph_id": "fg_01J9XK...",
  "nodes": [
    {
      "id": "ent_meth_7741",
      "type": "Method",
      "summary": "LiFSI-based localized high-concentration electrolyte; 4x cycle life (Chen 2025)",
      "relevance": 0.93,
      "why_included": "2-hop path: seed 'grid storage need' → SIGNALS_DEMAND_FOR → Method; PPR 0.81, semantic 0.88",
      "provenance": ["paper:arxiv:2503.01441", "signal:pitchbook:88123"]
    }
  ],
  "edges": [{ "source": "ent_meth_7741", "target": "ent_need_212", "relationship": "ADDRESSES", "weight": 0.77 }],
  "rendered_context": "...token-budgeted serialization...",
  "coverage_note": "Pruned 14 candidates: 9 stale (>24mo, unconfirmed), 3 staging-tier, 2 disconnected."
}
```

### Knowledge Graph Service (gRPC, excerpt)

```protobuf
service KnowledgeGraphService {
  rpc Query(QueryRequest) returns (QueryResponse);            // read-only Cypher, cost-capped
  rpc Mutate(MutateRequest) returns (MutateResponse);         // provenance required → staging tier
  rpc PromoteTier(PromoteTierRequest) returns (PromoteTierResponse); // curation / corroboration path
  rpc GetCommunity(GetCommunityRequest) returns (Community);
  rpc ResolveEntities(ResolveEntitiesRequest) returns (ResolveEntitiesResponse);
}
```

### Memory Service (gRPC, excerpt)

```protobuf
service MemoryService {
  rpc GetWorkingSet(GetWorkingSetRequest) returns (WorkingSet);   // assembled, token-budgeted
  rpc PutTaskMemory(PutTaskMemoryRequest) returns (Ack);
  rpc AppendEpisode(AppendEpisodeRequest) returns (Ack);
  rpc QueryExemplars(QueryExemplarsRequest) returns (ExemplarSet); // ICL few-shots by task-class
  rpc Consolidate(ConsolidateRequest) returns (ConsolidateReport); // mission-end + nightly
}
```

### Planning Service — `POST /v1/plans`

Request: `{ "ars_id": "ARS-142", "target_repos": ["svc-pricing"], "constraints": {"max_parallel_tasks": 4} }`
Response `201`:
```json
{
  "plan_id": "plan_8812",
  "task_dag": [
    {"task_id": "T1", "title": "Add electrolyte-model API endpoint", "depends_on": [],
     "blast_radius": {"services": ["svc-pricing"], "symbols": 14, "untested_fraction": 0.07},
     "risk_score": 0.21}
  ],
  "integration_strategy": "stacked branches → integration branch → protected main",
  "rollback_plan": "revert merge commit; no schema changes",
  "requires_approval": false
}
```

### Execution Service (gRPC, excerpt)

```protobuf
service ExecutionService {
  rpc StartMission(StartMissionRequest) returns (MissionHandle);     // launches Temporal workflow
  rpc GetMission(GetMissionRequest) returns (MissionStatus);
  rpc ExecuteInSandbox(SandboxRequest) returns (SandboxResult);      // backs code.execute
  rpc AbortMission(AbortMissionRequest) returns (AbortReport);       // compensation per §5.4
}
```

### Research Service — `POST /v1/sources/{source}/search`

```json
// request
{ "q": "localized high-concentration electrolyte cycle life", "filters": {"published_after": "2024-01-01"}, "limit": 20, "mode": "hybrid" }
// response 200
{ "results": [{ "paper_id": "pap_3321", "doi": "10.48550/arXiv.2503.01441", "title": "...",
   "score": 0.91, "graph_neighbors": ["ent_meth_7741"], "parse_status": "parsed" }], "next_cursor": "..." }
```

### Infrastructure Service (gRPC, excerpt — all mutations HITL-gated)

```protobuf
service InfrastructureService {
  rpc PlanChange(PlanChangeRequest) returns (ChangePlan);            // terraform plan rendering
  rpc ApplyChange(ApplyChangeRequest) returns (ApplyResult);         // requires approval_token
  rpc Release(ReleaseRequest) returns (ReleaseHandle);               // canary/bluegreen
  rpc Rollback(RollbackRequest) returns (RollbackResult);            // pre-authorized for infra agent
  rpc ProvisionTenant(ProvisionTenantRequest) returns (TenantResources); // pulumi path
}
```

### Audit Service

```protobuf
service AuditService {
  rpc Append(AppendRequest) returns (AppendAck);        // returns seq + event_hash; sync, <5ms p99
  rpc VerifyChain(VerifyChainRequest) returns (VerifyChainResponse);
  rpc Export(ExportRequest) returns (stream ExportChunk); // compliance packs
}
```
REST read: `GET /v1/audit/events?actor=agent:dev-7&mission=msn_4413&from=...` →
hash-chain-verifiable page of events.

### Approval Service — decide + verify

`POST /v1/approvals/{id}/decision`
```json
// request (destructive op example)
{ "decision": "approve", "typed_consequence": "DELETE dataset tenant_acme.signals_2024",
  "comment": "Confirmed with data owner." }
// response 200
{ "approval_token": "eyJhbGciOiJFZERTQSJ9...", "expires_at": "2026-06-10T12:14:00Z",
  "bound_params_hash": "9f2c...", "single_use": true }
```
`POST /v1/approvals/verify` (gateway-internal): `{ "token": "...", "params_hash": "9f2c..." }` →
`{ "valid": true, "approver": "usr_112", "checkpoint": "H4" }`

## 10.3 Cross-Cutting Rules

- Mutations idempotent via `idempotency_key` (24 h dedup window).
- Every response includes `trace_id`; agents echo it into tool ledgers.
- Versioning: URL `/v1/` (REST) and package version (gRPC); additive-only within a major; deprecations dual-served ≥ 90 days.
- Rate limits: per principal per service; agents additionally budget-governed (§2.3).

---

*Next: [Section 11 — Repository Organization](11-repository.md)*
