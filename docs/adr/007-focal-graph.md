# ADR-007: Focal Graph as the Task-Brief Mechanism

**Status:** Accepted (validation gate: P0 benchmark, OQ-1) · 2026-06-10

## Context
Agents need context briefs. Stuffing windows degrades reasoning and explodes cost;
plain RAG misses structure; GraphRAG community summaries answer global questions but
are too coarse for "implement task T against service S given research claim C".

## Decision
Every agent task brief and every human review artifact is a **Focal Graph**: seed
resolution → personalized PageRank with purpose-conditioned edge weights → blended
relevance scoring → Steiner-tree pruning to budget → per-node `why_included` +
`coverage_note`. RAG and community summaries remain for cheap lookups and global
questions respectively — three retrieval modes, one substrate.

## Consequences
- (+) Token-budgeted by construction; explainability is structural (drives the review UI and the Copilot-Paradox claims workflow).
- (+) PPR-push is graph-size-independent per query → interactive at TB scale.
- (−) New infra (ranking, pruning, cache) and a real failure mode: bad seeds → bad graph. Mitigated by hybrid seeding (ANN ∪ exact ∪ caller seeds) and the coverage note exposing pruning.
- Exit ramp: if P0 benchmark shows <15% lift over RAG baseline, degrade to GraphRAG-only and revisit (go/no-go at Phase 0 exit).
