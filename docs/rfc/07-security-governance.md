# Phase 7 — Security & Governance

> RFC-001 · Section 7 · Status: Draft
> Posture: assume agents are *competent but fallible insiders operating on attacker-influenced input*. Every control below is mechanical, not behavioral.

## 7.1 Threat Model

| Attack surface | Threat | Vector | Primary mitigations |
|---|---|---|---|
| Ingestion | **Prompt injection** | Instructions embedded in papers/web/READMEs | Taint tracking (§7.6), instruction/data separation, tool firewall |
| Ingestion | **Data poisoning** | Fabricated papers/signals steering opportunities | Trust tiers + corroboration (§4.5), source reputation, anomaly detection on graph deltas |
| Agent runtime | **Sandbox escape** | Malicious generated/dependency code | gVisor→Firecracker, no creds in sandbox, egress allowlist, syscall monitoring |
| Supply chain | **Dependency confusion / typosquats** | Agent adds packages | Private registry proxy, allow/deny lists, SCA scan in validation (stage 10) |
| Tooling | **Model misuse / scope creep** | Agent invokes tools beyond mission | OPA per-call policy, blast-radius ceilings, budget governors |
| Humans | **Insider threat** | Operator abuses approval power or exfiltrates | Dual-control for criticals, least-privilege RBAC, immutable audit, anomaly detection on approval patterns |
| Model layer | **Adversarial inputs to extraction** | Crafted text causing bad entities/relations | Constrained decoding vs ontology schema, confidence floors, staging tier |
| Audit | **Trail tampering** | Hiding malicious actions | Hash-chained append-only log, external anchor, write-once archive |

## 7.2 Policy Engine

OPA (Rego) sidecar at the MCP Gateway; every tool call evaluated against
`(principal, role, tool, resource, risk_context)`:

```rego
package r2pip.tools

default allow := false

allow if {
    input.tool.family == "perception"
    input.principal.kind == "agent"
    not rate_limited
}

allow if {
    input.tool.name == "deploy.release"
    input.principal.role == "infra_agent"
    valid_approval_token       # signed JWT: (service, revision, approver, expiry)
    input.context.taint != "external_untrusted"
}

deny_destructive if {
    input.tool.risk_class == "destructive"
    not input.approval.human_confirmed_consequence
}
```

Policies are versioned in-repo, reviewed like code, and *their evaluations are
themselves audit events* (decision + policy version hash).

## 7.3 HITL Checkpoints

Implemented by the **Approval Service**: an approval is a *signed, single-use,
short-lived token* binding the exact action parameters (service, revision, resource
IDs). The gateway verifies the signature and parameter hash — an approval for revision
A cannot authorize revision A′. Checkpoints H1–H8 per §5.5; destructive ops additionally
require typed-consequence confirmation; criticals (tenant deletion, audit-sink change,
policy change) require **dual control** (two distinct humans).

## 7.4 RBAC

| Role | Scope highlights |
|---|---|
| `viewer` | Read graph/dashboards; no approvals |
| `strategist` | H1 approvals; portfolio config |
| `architect` | H2/H3/H7/H8; autonomy threshold proposals (dual-control to enact) |
| `operator` | H5/H6; rollback; incident command |
| `tenant_admin` | User/role mgmt within tenant; data source config |
| `platform_admin` | Cross-tenant ops; dual-control for everything destructive |
| `agent:<type>` | Non-human principals; tool families per §2.2; **no approval-granting ability ever** |

Auth0 (OIDC/SAML SSO) for humans; SPIFFE-style workload identity for services/agents;
both map into the same OPA principal model.

## 7.5 Secrets

Vault + GCP KMS. Agents **never hold long-lived secrets**: the gateway injects
short-lived, scoped credentials (15-min TTL) server-side at execution — tool calls
reference *capability names*, not secrets. Sandboxes get zero secrets; deploy
credentials exist only inside the deploy MCP server. All secret reads audited;
rotation automated (≤90 d).

## 7.6 Prompt Injection Defense-in-Depth

1. **Provenance taint:** every datum carries `trusted | external_untrusted` from ingestion through focal-graph rendering into prompts.
2. **Instruction/data separation:** untrusted content is fenced and the assembler marks it `DATA — never instructions`; models are evaluated (red-team suite) on resisting fence-breaking.
3. **Tool firewall (the real control):** a context containing untrusted taint **downgrades the permitted toolset** for that agent turn — Perception/Computation stay; Action and `graph.write`-to-trusted are blocked. An injected instruction can at worst waste tokens; it cannot deploy, merge, or exfiltrate.
4. **Egress control:** sandboxes and agents reach the internet only via the allowlisting proxy; no arbitrary URLs from untrusted content are fetchable (anti-exfil via URL beacons).
5. **Injection sentinels:** ingestion scans for instruction-like patterns; flagged docs quarantine for human review.
6. **Output checks:** generated code scanned for secret-shaped strings, suspicious network calls, obfuscation markers before validation passes.

## 7.7 Audit, Provenance, Chain-of-Custody

Per the platform constraints, **every prompt, every tool call, every file modification**
emits an `AuditEvent`:

```
AuditEvent {
  event_id, ts, tenant_id,
  actor {kind: human|agent|system, id, on_behalf_of_mission},
  action {type: prompt|tool_call|file_mod|approval|policy_decision|deploy|login,
          tool?, params_hash, content_ref → WORM store},
  context {mission_id, task_id, trace_id, taint},
  prev_hash, event_hash        # hash chain
}
```

- **Immutability:** append-only Postgres staging → hourly sealed segments to GCS with **bucket lock (WORM)**; segment Merkle roots anchored to an external timestamping service. Tampering is detectable; deletion is impossible within retention.
- **Chain-of-custody:** any artifact (deployed binary, merged diff, ARS) resolves to the complete causal chain: papers → hypothesis → opportunity → approvals → prompts → diffs → tests → deploy — via provenance edges + audit linkage. This is also the reproducible-research mechanism: replay the chain with pinned model/prompt/tool versions.
- **Compliance logging:** SOC 2 / ISO 27001 / ISO 42001 / EU-AI-Act-aligned export packs generated from the audit stream (high-risk-system documentation, human-oversight evidence = approval records).

## 7.8 Model Governance

- **Model registry:** every model (extraction, codegen, ranking) registered with version, provider, eval scores, allowed task-classes.
- **Eval gate:** model/prompt changes pass offline eval suites (extraction F1, codegen pass@k, injection-resistance, refusal calibration) before serving; canaried like code.
- **Routing policy:** task-class → model tier mapping is governed config (cost + capability), dual-control to change.
- **Drift watch:** weekly defect-escape and eval-regression review; autonomy thresholds auto-tighten on regression (§1.7).

## 7.9 Residual-Risk Register

| Residual risk | Acceptance rationale | Compensating control |
|---|---|---|
| Novel injection bypassing fences | Cat-and-mouse domain | Tool firewall caps damage to read-only |
| Collusive poisoning across "independent" sources | Corroboration assumes independence | Source-cluster detection; human curation of high-impact promotions |
| Approval fatigue → rubber-stamping | Human-factors limit | Catch-rate sampling + autonomy auto-downgrade (§1.7) |
| Zero-day in gVisor/Firecracker | Industry-wide | Defense-in-depth: no secrets/creds in sandbox to steal |

---

*Next: [Section 8 — User Experience](08-ux.md)*
