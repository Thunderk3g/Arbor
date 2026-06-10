# ADR-010: Single Monorepo

**Status:** Accepted · 2026-06-10

## Context
The platform spans Go, Rust, Python, TypeScript, protos, prompts, and IaC. Changes are
frequently cross-cutting (proto + server + client + policy + infra). Additionally, the
platform analyzes codebases — including its own — so a unified blast-radius index over
our code is both a product demo and an engineering tool.

## Decision
One monorepo (Turborepo orchestration, per-language toolchains), layout per RFC §11.1.
CODEOWNERS doubles as the ownership map consumed by `blast.analyze`. CI runs on changed
targets only; prompts and policies are versioned, reviewed, and eval-gated like code.

## Consequences
- (+) Atomic cross-service changes; one CI policy surface; dogfooding blast radius from day one.
- (+) Agent-authored PRs target one repo with one pipeline — simpler claims verification.
- (−) CI tooling investment up front (target selection, caching); repo size growth managed with sparse checkouts for agent sandboxes.
- (−) Access partitioning is coarser than polyrepo; mitigated by CODEOWNERS + branch protection; revisit if compliance demands hard code segregation per team.
