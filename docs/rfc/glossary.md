# Glossary

| Term | Definition |
|---|---|
| **ARS** (Agent-Ready Specification) | The single contract artifact between research/product intent and engineering execution; human-approved intent + testable requirements + non-goals acting as a blast-radius ceiling (§5.1). |
| **A2A** | Agent2Agent protocol: capability discovery (Agent Cards) and task delegation between agents (§2.5). |
| **ACP** | Agent Communication Protocol: REST-native conversational/multipart messaging between collaborating agents (§2.5). |
| **Blast radius** | The computed impact set (symbols, services, tests, data) of a proposed change; feeds the risk score and caps agent scope (§5.3). |
| **Claims sheet** | Structured assertions an agent must emit with any diff ("does X, cannot affect Y, tested by Z"); humans review claims, the platform verifies them mechanically (§1.7). |
| **Contract-net** | Bidding protocol: supervisor broadcasts a task, idle agents bid, award by capability×availability (§2.8). |
| **Copilot Paradox** | As automation quality rises, human review attention falls exactly when residual errors get subtler; mitigated structurally (§1.7). |
| **Data-to-Product field** | The non-pipeline architecture: persistent knowledge substrate + asynchronous loops integrating only through it (§1.1, ADR-001). |
| **Dissent** | A first-class ACP artifact blocking merge until supervisor resolution; mechanized disagree-and-commit (§2.8). |
| **Focal Graph** | Minimal, ranked, *explained* subgraph sufficient for one task; the standard agent brief and review artifact (§4.4, ADR-007). |
| **GraphRAG** | Retrieval over a knowledge graph with hierarchical community summaries; used for global "state of domain" questions (§4.2). |
| **HITL checkpoints H1–H8** | The eight defined human intervention points from opportunity approval to post-hoc audit sampling (§5.5). |
| **Mission / mission cell** | One Opportunity → product increment, executed by a supervised agent roster under a Temporal workflow (§2.1). |
| **MCP** | Model Context Protocol: how agents access all tools and resources, via the single gateway (§3, ADR-004). |
| **One-way door** | Hard-to-reverse action (delete, schema contract, external publish, spend); always HITL-gated with typed-consequence confirmation (§1.5). |
| **PPR** | Personalized PageRank; the expansion algorithm in focal extraction, approximated with push updates for graph-size-independent latency (§4.4). |
| **Risk score R** | Normalized [0,1] blend of blast radius, reversibility, data sensitivity, novelty; selects the autonomy mode (§1.6). |
| **Staging / trusted tiers** | Graph trust levels; automated writes land in staging, promotion requires corroboration or curation — the poisoning defense (§4.5). |
| **Swanson linking (A–B–C)** | Discovering that A relates to C via shared intermediate B across disconnected literatures; the BI-Agent's arbitrage primitive (§2.2). |
| **Taint / tool firewall** | `trusted|external_untrusted` provenance flag whose presence in context mechanically blocks Action tools for that turn (§7.6, ADR-008). |
| **WORM** | Write-once-read-many storage (GCS bucket lock) sealing hourly audit segments; tampering detectable, deletion impossible in retention (§7.7). |
| **70/20/10** | Innovation portfolio allocation: core / adjacent / experimental, governed on the innovation dashboard (§8.2). |
