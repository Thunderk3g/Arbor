# ADR-006: Polyglot Persistence, One System of Record per Entity

**Status:** Accepted · 2026-06-10

## Context
Workloads are heterogeneous: multi-hop typed traversal (graph), ANN retrieval (vectors),
transactional state + RLS (relational), TB-scale scans (warehouse), immutable blobs
(object store). No single engine serves all without severe compromise; but uncontrolled
polyglot yields consistency chaos.

## Decision
Five engines — Neo4j, Milvus (Pinecone in MVP), PostgreSQL, BigQuery, GCS — with a hard
rule: **every entity has exactly one system of record** (placement table, RFC §9.1);
all other copies are projections rebuilt from the SoR, refreshed by declared pipelines
(CDC/export), never written directly.

## Consequences
- (+) Each workload on its best engine; capacity plans per engine are simple.
- (+) Disaster recovery = restore SoRs, replay projections.
- (−) Projection lag is a feature contract (e.g., BigQuery graph mirror is T+1 day); UIs label freshness.
- (−) Five engines of operational surface → managed services in MVP (Aura, Pinecone, Cloud SQL), self-host only where unit economics demand (Milvus, Neo4j at scale).
