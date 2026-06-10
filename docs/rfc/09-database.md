# Phase 9 — Database Design

> RFC-001 · Section 9 · Status: Draft
> Polyglot persistence: **Neo4j** (graph) · **Milvus** (vectors) · **PostgreSQL** (transactional/state/audit staging) · **BigQuery** (analytics/telemetry) · **GCS** (blobs/WORM audit). Each entity has exactly one system of record; others hold projections.

## 9.1 Entity Placement

| Entity | System of record | Projections |
|---|---|---|
| EntityNode, RelationEdge | Neo4j | BigQuery (analytics mirror, daily export) |
| VectorStore | Milvus | — |
| ResearchPaper | GCS (raw) + Neo4j (node) | BigQuery metadata table |
| CodeBlock | Neo4j (code graph) | Milvus (symbol embeddings) |
| MarketSignal | BigQuery | Neo4j (promoted aggregates) |
| SoftwareArtifact, Task, ApprovalRequest | PostgreSQL | Neo4j (platform graph nodes) |
| AgentMemory | Redis (hot) + PostgreSQL (checkpoint) | Neo4j episodic (consolidated) |
| ExecutionLog | BigQuery (volume) | — |
| AuditEvent | PostgreSQL staging → GCS WORM | BigQuery (query mirror) |

## 9.2 ER Diagrams

### Knowledge core

```mermaid
erDiagram
    ENTITY_NODE {
        uuid id PK
        varchar type "Method|Claim|Company|..."
        varchar canonical_name
        jsonb metadata
        float confidence
        varchar tier "staging|trusted"
        uuid tenant_id
        timestamptz created_at
        timestamptz updated_at
    }
    RELATION_EDGE {
        uuid id PK
        uuid source FK
        uuid target FK
        varchar relationship
        float weight
        jsonb evidence_spans
        uuid provenance_id FK
        uuid tenant_id
    }
    VECTOR_STORE {
        uuid id PK
        uuid ref_id "entity or chunk"
        varchar namespace "tenant.modality"
        vector embedding "dim 1024-3072"
        text chunk_text
        jsonb metadata
    }
    RESEARCH_PAPER {
        uuid id PK
        varchar doi
        varchar title
        jsonb authors
        date published
        varchar source "arxiv|pubmed|patent|..."
        varchar raw_uri "gcs path"
        varchar parse_status
        uuid tenant_id
    }
    CODE_BLOCK {
        uuid id PK
        uuid repo_id FK
        varchar symbol_fqn
        varchar kind "function|class|module"
        varchar content_hash
        int loc
        jsonb ast_metrics
        varchar scip_ref
    }
    MARKET_SIGNAL {
        uuid id PK
        varchar signal_type "funding|launch|filing|pricing"
        varchar subject_entity
        jsonb payload
        float strength
        timestamptz observed_at
        varchar source_feed
        uuid tenant_id
    }
    ENTITY_NODE ||--o{ RELATION_EDGE : source
    ENTITY_NODE ||--o{ RELATION_EDGE : target
    RESEARCH_PAPER ||--o{ ENTITY_NODE : "extracted into"
    CODE_BLOCK ||--o| ENTITY_NODE : "mirrored as"
    MARKET_SIGNAL ||--o| ENTITY_NODE : "promoted as"
    ENTITY_NODE ||--o{ VECTOR_STORE : "embedded"
```

### Execution & governance core

```mermaid
erDiagram
    TASK {
        uuid id PK
        uuid mission_id FK
        uuid ars_id FK
        varchar status "pending|leased|active|validating|done|failed"
        uuid assignee_agent_id
        timestamptz lease_expires_at
        jsonb acceptance_criteria
        jsonb blast_radius
        float risk_score
        uuid tenant_id
    }
    SOFTWARE_ARTIFACT {
        uuid id PK
        uuid task_id FK
        varchar kind "diff|image|package|migration"
        varchar digest "immutable"
        varchar uri
        jsonb claims_sheet
        jsonb provenance_chain
    }
    AGENT_MEMORY {
        uuid id PK
        uuid agent_instance_id
        uuid mission_id FK
        varchar scope "session|task|episodic"
        jsonb content
        int token_estimate
        timestamptz expires_at "null for episodic"
    }
    EXECUTION_LOG {
        uuid id PK
        uuid task_id FK
        uuid agent_instance_id
        varchar phase
        varchar tool_name
        jsonb params_summary
        varchar result_status
        varchar trace_id
        timestamptz ts
    }
    APPROVAL_REQUEST {
        uuid id PK
        varchar checkpoint "H1..H8"
        uuid subject_id "mission|task|deploy|op"
        jsonb evidence_bundle
        float risk_score
        varchar status "pending|approved|rejected|expired"
        uuid approver_user_id
        varchar approval_token_hash
        timestamptz decided_at
        uuid tenant_id
    }
    AUDIT_EVENT {
        uuid event_id PK
        bigint seq "monotonic per tenant"
        uuid tenant_id
        jsonb actor
        jsonb action
        jsonb context
        char64 prev_hash
        char64 event_hash
        timestamptz ts
    }
    TASK ||--o{ SOFTWARE_ARTIFACT : produces
    TASK ||--o{ EXECUTION_LOG : emits
    TASK ||--o{ APPROVAL_REQUEST : "may require"
    APPROVAL_REQUEST ||--o{ AUDIT_EVENT : "recorded as"
    AGENT_MEMORY }o--|| TASK : "scoped to"
```

## 9.3 Indexing Strategy

| Store | Index | Purpose |
|---|---|---|
| Neo4j | btree on `:Entity(id)`, composite `(tenant_id, type)`, `(tenant_id, canonical_name)` | lookups, tenant scoping |
| Neo4j | full-text on `canonical_name, aliases` | seed resolution |
| Neo4j | relationship index on `relationship` + `weight` | typed traversal (PPR) |
| Milvus | HNSW (M=16, efC=200) per namespace; scalar filters on `tenant`, `modality`, `tier` | ANN with filtered search; IVF_PQ for cold namespaces |
| Postgres | `task(status, lease_expires_at)` partial index on active statuses | scheduler scans |
| Postgres | `approval_request(tenant_id, status) WHERE status='pending'` | inbox |
| Postgres | `audit_event(tenant_id, seq)` unique; BRIN on `ts` | chain verification, range scans |
| BigQuery | partition `execution_log`/`telemetry`/`market_signal` by `DATE(ts)`, cluster by `(tenant_id, mission_id)` / `(tenant_id, signal_type)` | scan-cost control |

## 9.4 Partitioning Strategy

- **Tenant first, everywhere.** Postgres: `tenant_id` columns + RLS policies (MVP) → schema-per-tenant for large tenants. Neo4j: logical partition via tenant label + composite indexes (MVP) → database-per-tenant (Enterprise, also the VPC story). Milvus: collection-per-tenant above size threshold, partition-key below. BigQuery: dataset-per-tenant ("workspace"), per-dataset quotas.
- **Within tenant:** graph partitions by domain layer (research/code/market/platform); cross-layer edges are first-class but counted — a layer-cut metric guards against pathological fan-out. Time-partition everything event-shaped (BigQuery native; Postgres `pg_partman` monthly on `execution_log`, `audit_event` staging).

## 9.5 Scaling Strategy

| Store | 1 TB → 10 TB+ path |
|---|---|
| Neo4j | Aura (MVP) → self-hosted causal cluster: 1 writer + read replicas; analytics offloaded to BigQuery mirror; if write ceiling hit → evaluate sharded property graph or layer-split databases |
| Milvus | Pinecone (MVP) → Milvus on GKE: segment-based scale-out on GCS; QPS via querynode autoscaling; tiered: hot HNSW in memory, cold IVF_PQ on disk |
| Postgres | Vertical first (transactional volume is modest) + read replicas; partition pruning; audit volume routed to WORM/BigQuery so Postgres stays small |
| BigQuery | Native serverless; cost control = partition discipline + per-tenant byte quotas + materialized views for dashboard queries |
| Redis | Memorystore cluster mode; STM is TTL-bound so working set stays flat per concurrent mission |

Capacity anchor (Enterprise design point): 100 tenants × 10 concurrent missions ×
10 agents ≈ 10k concurrent agent contexts; ~5k tool calls/s at gateway (Go, horizontally
trivial); graph ~10⁹ nodes / 10¹⁰ edges aggregate — within partitioned-Neo4j +
PPR-push envelope per §4.6.

---

*Next: [Section 10 — APIs](10-apis.md)*
