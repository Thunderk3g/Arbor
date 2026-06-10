# Example — Golden Mission Walkthrough

An end-to-end trace of one mission, MSN-4413, showing how every RFC section composes.
This narrative doubles as the spec for the `tests/e2e` golden-mission scenario.

## Cast

- **Tenant:** `acme-energy` · **Corpus:** 40k battery-research papers, market feed, telemetry from their pricing service.
- **Humans:** Priya (strategist), Marcus (architect), Dana (operator).

## Day 0 — Perception & Insight (§4, §2.2)

1. Ingestion workflows parse three new arXiv papers on localized high-concentration electrolytes (LHCE). Extraction emits `Method`, `Claim`, `Metric` nodes → **staging tier**, taint `external_untrusted`, provenance attached (`graph.write`).
2. Two claims corroborate an existing trusted claim → promotion job moves the `Method` node to **trusted**.
3. BI-Agent's nightly sweep runs `graph.community` + `focal.extract(purpose=opportunity_mining)`. PPR surfaces a 2-hop path: `MarketSignal(grid-storage RFP wave) —SIGNALS_DEMAND_FOR→ Need(cycle-life modeling) ←ADDRESSES— Method(LHCE degradation model)`. Opportunity score 0.81 → writes `Opportunity` node.

## Day 1 — Specification (H1)

4. PO-Agent drafts a PR/FAQ: *"Add electrolyte cycle-life prediction to acme's pricing API"* + ARS-142 (FRs, ACs, non-goals: "no schema changes to billing"). `spec.validate` passes.
5. Priya gets the digest in Slack, opens the **focal graph view**, checks `why_included` on the LHCE node and the coverage note ("pruned 3 staging-tier candidates"), edits the intent paragraph inline (Yjs), approves **H1**. Approval Service issues a token; audit events 88121–88137 record the chain.

## Day 1–2 — Planning (H2)

6. Temporal mission workflow spawns the cell. Head Engineer runs `ast.analyze` + `deps.graph` + `blast.analyze` on `svc-pricing`: 14 symbols, 1 service, untested fraction 0.07 → **R = 0.34 (supervised mode)**.
7. Task DAG: T1 model port (from paper's reference implementation, license-checked), T2 API endpoint, T3 backtest harness. Plan + rollback strategy ("revert merge; no migrations") goes to Marcus. He approves the **plan, not the diff** (H2).

## Day 2–3 — Build & Validate

8. Contract-net: Dev-7 wins T1/T2 (capability 0.91 on `python-numerics` task-class), Dev-3 takes T3. Leases granted; briefs are focal graphs (`purpose=code_task_brief`) — note T1's brief contains the paper's equations *as fenced DATA* (taint propagated → Dev-7's turns with that content have Action tools blocked; it writes code in the sandbox via Computation tools, commits later from a clean-context turn referencing the validated artifact).
9. Dev-7 iterates in `code.execute` sandboxes (network: `package_registries` for one `pip install`, screened by the egress proxy). Emits diff + **claims sheet**: "touches 11 symbols (≤14 declared), cannot affect billing, tested by 28 new cases."
10. QA-1 runs `test.generate` + mutation testing (score 0.74 ≥ baseline 0.7). Files one **dissent**: AC3's tolerance ambiguous. Head Engineer resolves (tightens tolerance), Dev-7 revises, validation passes. Claims sheet mechanically verified against blast radius — diff within declared scope.

## Day 4 — Merge, Deploy (H5), Soak

11. R = 0.34 → supervised: Marcus approves the claims sheet (90 seconds — he reads claims, spot-opens one hunk). Merge to protected branch.
12. Deploy workflow requests **H5**. Dana reviews canary plan (5→25→50→100, abort on p99 latency +10% or error rate 2×), approves → single-use token bound to the image digest. Infra Agent calls `deploy.release`; gateway verifies token+params hash.
13. Canary step 2 shows p99 +4% — within threshold; rollout completes. 24-h soak detectors armed; SLO baseline registered.

## Day 5+ — Evolution (stage 13)

14. A week later, telemetry shows the endpoint's heaviest users are battery *recyclers*, not grid operators — an unanticipated segment. The evolution loop writes a `TelemetryEvent → Need?` hypothesis; BI-Agent scores it; a new Opportunity lands in Priya's inbox. The loop closes.

## What the audit trail can answer afterwards

- *"Why does this feature exist?"* → provenance chain: 3 papers + 1 market signal + Priya's H1 token.
- *"Who approved production?"* → Dana's H5 token, bound to digest `sha256:9f2c…`, in audit segment 2026-06-14T10, Merkle-anchored.
- *"Could the paper have injected anything?"* → every turn where untrusted content was in context shows Action tools blocked in the gateway decision log.
- *"Reproduce it"* → replay the chain with pinned model/prompt/tool versions from the execution log.
