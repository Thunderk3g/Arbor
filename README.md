# RFC-001 — Research-to-Product Intelligence Platform (R2P-IP)

**Status:** Draft for Review · **Type:** Architecture RFC + Implementation Blueprint
**Authors:** Platform Architecture Group · **Target audience:** Founding engineers, Staff+ engineers
**Created:** 2026-06-10 · **Supersedes:** None

R2P-IP transforms multimodal research (papers, market signals, telemetry, code) into
executable, continuously evolving software products through a decentralized swarm of
autonomous agents collaborating over a shared knowledge graph with GraphRAG and
Focal Graph reasoning — under enforced human strategic oversight.

## Document Map

| # | Document | Contents |
|---|----------|----------|
| 0 | [Planning](docs/rfc/00-planning.md) | ToC, architectural overview, subsystems, assumptions, risks, open questions, MVP vs Enterprise |
| 1 | [Architectural Philosophy](docs/rfc/01-philosophy.md) | Data-to-Product framework, learning loops, Copilot Paradox, human-AI collaboration |
| 2 | [Swarm Multi-Agent Architecture](docs/rfc/02-swarm-architecture.md) | Agent roster, lifecycle, MCP/ACP/A2A, coordination, failure recovery |
| 3 | [Tool Ecosystem](docs/rfc/03-tool-ecosystem.md) | Perception/Computation/Action/Memory MCP tools + API specs |
| 4 | [Knowledge Graph & Memory](docs/rfc/04-knowledge-memory.md) | Dual memory, GraphRAG, ontology, Focal Graph generation, ER diagrams |
| 5 | [Autonomous SWE Workflow](docs/rfc/05-ase-workflow.md) | 13-stage deterministic workflow, blast radius, rollback, HITL points |
| 6 | [Infrastructure](docs/rfc/06-infrastructure.md) | Kubernetes, serverless analytics, sandboxing, eventing, observability, IaC |
| 7 | [Security & Governance](docs/rfc/07-security-governance.md) | Policy engine, RBAC, prompt-injection defense, audit, threat model |
| 8 | [User Experience](docs/rfc/08-ux.md) | Focal graph viz, swarm timeline, HITL approval UI, 70/20/10 dashboard |
| 9 | [Database Design](docs/rfc/09-database.md) | ERDs, indexing, partitioning, scaling |
| 10 | [APIs](docs/rfc/10-apis.md) | REST/gRPC/OpenAPI for all 10 services with examples |
| 11 | [Repository Organization](docs/rfc/11-repository.md) | Monorepo layout, CI/CD organization |
| 12 | [Phased Roadmap](docs/rfc/12-roadmap.md) | Phase 0→5, team sizing, milestones, risk, success metrics |
| A | [Implementation Checklists](docs/rfc/13-implementation-checklists.md) | Build-order checklists, MVP exit gate, definition of done |
| — | [Architecture Decision Records](docs/adr/README.md) | ADR-001…010: the load-bearing decisions and their trade-offs |
| — | [Glossary](docs/rfc/glossary.md) | Platform vocabulary |
| — | [Golden Mission Walkthrough](examples/mission-walkthrough.md) | End-to-end example tracing every subsystem |

## Reading Order

- **Founders / product:** 0 → 1 → 8 → 12
- **Staff engineers:** 0 → 2 → 4 → 5 → 6 → 7
- **Implementers:** 3 → 9 → 10 → 11

## Non-Negotiable Constraints (enforced architecturally, see §7)

1. Human-in-the-Loop approval for all destructive/irreversible actions.
2. Every tool call, prompt, and file modification is logged to an immutable audit trail.
3. All agent code execution occurs inside hardened sandboxes (no ambient credentials).
4. Prompt-injection defense in depth (taint tracking, content/instruction separation, tool firewalls).
5. Terabyte-scale data, enterprise SaaS multi-tenancy, zero-downtime deploys.
6. Explainability and observability are first-class: every autonomous decision is reconstructible.
