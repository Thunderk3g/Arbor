# Phase 14 (Appendix B) — Agent Prompting & Scaffolding Standards

> RFC-001 · Appendix B · Status: Draft
> Source basis: Anthropic's Claude Fable 5 prompting guidance, translated into R2P-IP design requirements. Prompt packs live in `agents/prompts/`, are versioned and eval-gated like code (§7.8, §11.2); this appendix is their normative spec.

## B.1 Why this appendix exists

The swarm's agents (§2) are powered by frontier Claude models (Fable 5 class). Model
behavior is therefore a *platform dependency* with its own upgrade semantics: capability
improvements change what instructions are needed, and over-prescriptive prompts written
for older models actively degrade newer ones. This appendix sets the standards the
prompt assembler (§4.1) and prompt packs must follow, and the review cadence that keeps
them current.

## B.2 Model & Effort Routing

Effort is the primary intelligence/latency/cost control. Routing is governed config
(§7.8 model governance, dual-control to change), keyed by agent role and task-class:

| Agent / task-class | Effort | Rationale |
|---|---|---|
| Head Engineer: decomposition, blast-radius reasoning, dissent arbitration | `xhigh` | Capability-sensitive; errors compound downstream (R1) |
| BI-Agent: opportunity mining sweeps | `high` | Deep synthesis, but bounded by focal-graph inputs |
| PO-Agent: PR/FAQ + ARS drafting | `high` | Human-reviewed output; quality over latency |
| Developer Agent: implementation tasks | `high` (default) / `medium` for mechanical refactors | First-shot correctness pays for itself in fewer QA cycles |
| QA Agent: test generation, claims verification | `high` | Verification rigor is the point |
| Routine: formatting, summarization, digest assembly | `low`/`medium` | Lower effort on Fable-class models still exceeds prior-generation `xhigh` |

**Fallback policy:** Fable-class models return `stop_reason: "refusal"` from safety
classifiers (offensive-cyber, bio, reasoning-extraction). The agent runtime configures
automatic fallback to Opus 4.8 for benign-but-misclassified work; repeated refusals on
a task quarantine it for human triage rather than retry-looping (budget governor, §2.3).
Platform policy independently denies those domains anyway (§7) — fallback is for false
positives, not a bypass.

## B.3 Prompt Pack Standards

Every agent system prompt is assembled from standard blocks. Normative requirements:

1. **Brevity by selection, not compression.** Output instructions follow the "lead with the outcome; drop details that don't change what the reader does next; complete sentences, no arrow-chains" pattern. Claims sheets and ValidationReports are *readable artifacts for humans* (§1.7) — this block is mandatory in every pack.
2. **Act-when-able.** "When you have enough information to act, act; give a recommendation, not a survey." Prevents high-effort deliberation loops on routine stages.
3. **Scope discipline.** "Don't add features, refactor, or introduce abstractions beyond what the task requires" — the prompt-level twin of the mechanical blast-radius ceiling (§5.3). Defense in depth: the prompt discourages scope creep; validation auto-rejects it.
4. **Boundaries.** Agents asked to *assess* (QA verdicts, BI hypotheses) must not *act*: "the deliverable is your assessment; report findings and stop." Action requires a task lease.
5. **No reasoning-echo instructions — ever.** Packs must not instruct agents to transcribe or explain internal reasoning as output (triggers `reasoning_extraction` refusals and elevates fallbacks). Claims sheets are *evidence-grounded assertions referencing tool results*, not thinking transcripts. Reasoning visibility for audit comes from structured thinking blocks and the tool ledger, never from "show your work" prompting. CI lints packs for this anti-pattern.
6. **Autonomous-operation reminder.** Agents run unattended between H-gates: "you are operating autonomously; for reversible actions that follow from the task, proceed; pause only at defined checkpoints (H1–H8), destructive actions, or genuine scope changes — then ask and end the turn rather than ending on a promise."

## B.4 Grounded Progress Claims

The single highest-leverage instruction for long runs, mandatory in every pack:

> Before reporting progress, audit each claim against a tool result from this session.
> Only report work you can point to evidence for; if something is not yet verified, say
> so explicitly. If tests fail, say so with the output; if a step was skipped, say that.

Platform enforcement on top: every claims-sheet line must cite a `tool_ledger` entry ID
(task memory, §4.1); the claims verifier rejects uncited claims mechanically. Prompt
discourages fabrication; verification makes it non-viable. This pairing is the
anti-fabrication design for stage 10 (§5.1).

## B.5 Long-Turn & Long-Run Scaffolding

- **Turns are long now.** Single agent turns at high effort can run many minutes. Temporal activity timeouts and heartbeats are sized accordingly (activity heartbeat 60 s, start-to-close per task-class p99 × 3); the orchestrator checks on agents asynchronously via checkpoints — never blocks a workflow thread on a single agent turn.
- **No context-budget countdowns.** The prompt assembler must not surface remaining-token counts to agents (triggers premature wrap-up/self-trimming). Budget management is the runtime's job: at 70% window, the assembler summarizes and rebuilds (§4.1); the agent just keeps working. Where a budget signal is unavoidable, the pack includes the "you have ample context; do not stop on account of context limits" reassurance.
- **Early-stop guard.** The runtime detects text-only turn endings that state intent without a tool call ("I'll now run X") and re-prompts with "continue — go ahead end to end" once before escalating; pairs with the checkpoint instruction so the only legitimate pauses are H-gates.
- **Intent context.** Every brief carries the *why*: the ARS intent paragraph and the mission's place in the portfolio ("I'm working on [mission] for [tenant]; they need [outcome]; with that in mind: [task]"). Fable-class models measurably use intent to connect tasks to relevant context instead of guessing.

## B.6 Verification Scaffolding

- **Fresh-context verifiers outperform self-critique.** Already structural in R2P-IP: QA agents never inherit the Developer's transcript — they receive the diff, claims sheet, and ARS in a fresh context (§2.2). This appendix makes it normative: *no verifier may share a context window with the producer of the artifact it verifies.*
- **Interval self-checks.** Long implementation tasks include: "establish a method for checking your work; every N steps, verify against the acceptance criteria with a fresh-context subagent." The Developer's runtime exposes this as a scoped sub-agent spawn (Computation-only toolset, same lease).
- **Parallel subagents.** Fable-class models delegate well. Head Engineer packs instruct: "delegate independent subtasks and keep working while they run; intervene if a subagent goes off track" — implemented over A2A task delegation (§2.5), with the contract-net award as the delegation primitive.

## B.7 `notify.surface` — the send-to-user tool

New Action-family MCP tool (extends §3.1): verbatim, mid-turn delivery of content the
human must see exactly as written, without ending the agent's turn.

```jsonc
{
  "name": "notify.surface",
  "description": "Display a message verbatim to mission watchers (swarm timeline + subscribed channels) without ending the turn. For deliverables, numeric progress, or direct replies to a human's mid-mission question.",
  "inputSchema": {
    "type": "object",
    "required": ["message"],
    "properties": {
      "message": { "type": "string", "maxLength": 8000 },
      "kind": { "enum": ["progress", "deliverable", "reply", "warning"], "default": "progress" },
      "reply_to": { "type": "string", "description": "Thread/message ID when answering a human question" }
    }
  }
}
```

Rationale: tool inputs are never summarized, so content arrives intact; the swarm
timeline (§8.2) renders it as an attributed agent message; audited like every tool call.
Rate-limited (Action family); `kind=progress` capped per task to prevent narration spam.

## B.8 Memory & Lesson Files

The episodic store (§4.1) adopts the lesson-file discipline:

- One lesson per episode node, one-line summary field first (the exemplar service retrieves on summary embeddings).
- Record corrections *and* confirmed approaches, each with *why it mattered* (the consolidation worker rejects lesson writes without a rationale field).
- No duplicates: consolidation runs a similarity check and updates the existing lesson instead; lessons contradicted by later outcomes are deprecated, not deleted (provenance preserved).
- **Bootstrap reflection:** on tenant onboarding and quarterly, a reflection job replays mission history with subagents to distill themes into the lesson store — the "review past sessions" pattern, productized.

## B.9 Prompt Pack Lifecycle (instructions are liabilities)

Model upgrades invert the usual dependency rule: *more capable model ⇒ fewer
instructions needed, and stale instructions degrade output.* Therefore:

| Policy | Mechanism |
|---|---|
| Every pack block carries an owner and a "why this block exists" note | Pack schema; CI rejects anonymous blocks |
| Quarterly simplification pass per pack | Eval harness A/Bs the pack against a minimized variant; if the minimized variant matches or beats baselines, it ships |
| Model-upgrade gate re-runs all pack evals | §7.8 eval gate; packs that regress on the new model are flagged for de-prescription first, augmentation second |
| Anti-pattern lints | No reasoning-echo (B.3.5), no enumerated behavior lists where one steering sentence suffices, no duplicated platform-enforced rules unless defense-in-depth is intended (and marked) |

The test for any instruction: *does removing it measurably hurt evals on the current
model?* If not, it goes. This keeps the platform's "model dependency" current the same
way dependency bots keep libraries current.

---

*Return to [README](../../README.md).*
