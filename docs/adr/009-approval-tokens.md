# ADR-009: Signed Single-Use Approval Tokens for HITL

**Status:** Accepted · 2026-06-10

## Context
"Human approved it" must be cryptographically bindable to *exactly what* was approved.
A boolean `approved` flag on a request row can be raced, replayed, or applied to a
mutated action (approve revision A, deploy revision A′).

## Decision
The Approval Service issues a short-lived, single-use JWT (EdDSA) binding
`(checkpoint, action type, params_hash, approver, expiry)`. The MCP gateway verifies
signature + parameter hash at execution; mismatch or reuse → fail closed. Destructive
class additionally requires the typed-consequence string captured in the evidence
bundle; criticals require dual-control (two tokens).

## Consequences
- (+) Approval is unforgeable, unreplayable, and parameter-exact; the token hash in the audit chain is the human-oversight evidence regulators ask for (EU AI Act Art. 14 alignment).
- (+) Chat-ops approvals are exactly as strong as web approvals — same token path.
- (−) Any parameter change after approval (even a retry with a new image digest) requires re-approval. Correct, but demands good UX for "re-approve with diff highlighted".
- (−) Key management for the signing key is now critical-path (KMS-backed, rotated).
