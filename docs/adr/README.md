# Architecture Decision Records

Format: [MADR-lite] — Status · Context · Decision · Consequences. One file per decision.
ADRs record *why*; the RFC records *what*. When they conflict, the newer ADR wins and the RFC gets amended.

| # | Decision | Status | RFC ref |
|---|----------|--------|---------|
| [001](001-field-architecture.md) | Data-to-Product field over linear pipeline | Accepted | §1.1 |
| [002](002-supervised-swarm.md) | Hybrid supervised swarm topology | Accepted | §2.1 |
| [003](003-temporal-spine.md) | Temporal as the deterministic spine | Accepted | §5 |
| [004](004-mcp-gateway-chokepoint.md) | Single MCP gateway choke point | Accepted | §3.3 |
| [005](005-protocol-split.md) | MCP / A2A / ACP protocol split | Accepted | §2.5 |
| [006](006-polyglot-persistence.md) | Polyglot persistence, one system of record per entity | Accepted | §9.1 |
| [007](007-focal-graph.md) | Focal Graph as the task-brief mechanism | Accepted | §4.4 |
| [008](008-taint-tool-firewall.md) | Taint-based tool firewall for prompt injection | Accepted | §7.6 |
| [009](009-approval-tokens.md) | Signed single-use approval tokens for HITL | Accepted | §7.3 |
| [010](010-monorepo.md) | Single monorepo | Accepted | §11 |
| [011](011-python-reference-implementations.md) | Python reference implementations for protocol cores | Accepted | §11, App. A |
