# ADR-011: Python Reference Implementations for Protocol Cores

**Status:** Accepted · 2026-06-10

## Context
RFC §11 specifies Go for the core services (audit, approval, gateway). The first
vertical slices — audit hash chain, approval tokens, ontology validation — are
security-critical protocol cores whose correctness matters more than their host
language. The initial development environment has Python 3.10 and Node 20 toolchains
but no Go; shipping untested Go would violate the verification-before-completion rule
that everything merged must have run its tests.

## Decision
Implement the protocol cores as **tested Python reference implementations**
(`backend/audit`, `backend/approval`, `graph/ontology`), with behavior pinned by their
pytest suites. The suites — not the Python code — are the contract: hash-chain linking
and tamper detection, token parameter-binding and replay rejection, ontology
validation rules. The Go ports (planned when the MCP gateway lands, Phase 1 §A.3)
must pass equivalent test vectors; a shared `testdata/` of golden vectors will be
extracted from the Python suites at port time.

The ontology package stays Python permanently (it serves the Python extraction
pipeline, §4.2) — only audit/approval are ports-in-waiting.

## Consequences
- (+) Working, tested protocol cores now; the cryptographic and chaining semantics are executable specification rather than prose.
- (+) FastAPI apps make the services runnable for local integration and demos.
- (−) Throughput of the Python audit appender is far below the Go target (§9.5 anchor: ~5k events/s); acceptable for reference/demo, flagged as a port blocker before Internal Alpha load.
- (−) Temporary divergence from RFC §11 language table; this ADR is the tracking record. Debt ledger entry: "Go port of audit + approval cores" due before Phase 2 exit.
