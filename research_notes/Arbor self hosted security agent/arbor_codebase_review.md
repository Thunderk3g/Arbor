# Arbor codebase review: how well does the safety machinery serve as the base of a self-hosted security agent?

Conventions used in these notes

- Reviewed commit: `af8af28` (tip of `main`; the working branch `claude/intelligent-pasteur-atxn6c` adds only `research_notes/` commits on top, with no code changes, verified with `git diff af8af28 HEAD -- . ':!research_notes'` returning nothing). Date of review: 2026-11-10.
- All citations are `path:line` relative to the repo root `/home/user/Arbor`. Short forms: `gateway/` = `backend/gateway/r2pip_gateway/`, `approval/` = `backend/approval/r2pip_approval/`, `audit/` = `backend/audit/r2pip_audit/`, `plat/` = `platform/r2pip_platform/`, `focal/` = `graph/focal/r2pip_focal/`, `onto/` = `graph/ontology/r2pip_ontology/`, `mem/` = `memory/r2pip_memory/`.
- Three evidence grades are used throughout: **[CODE]** read directly in source; **[PROBE]** verified by running a throwaway script against the real packages (outputs quoted verbatim; scripts lived in a session scratch dir and were not added to the repo; each probe is small enough to re-create from the description); **[DOC-ONLY]** stated in an ADR/RFC but with no implementation.
- Size of what exists: about 4,000 lines of Python in 7 packages, 219 tests, everything in one process and in memory. There is no LLM call, no network call, no subprocess, no database and no file write anywhere in non-test code (the only file read is the ontology YAML, `onto/loader.py:99`).
- One-sentence overall finding: the repo contains correct, well-tested *protocol kernels* (hash chain, EdDSA single-use token, ordered policy function, ontology validator, PPR retrieval, prompt assembler) wrapped around a scripted demo; almost every property a security agent needs from them (who is calling, what is the target, was the context really tainted, did the human see what they signed, can the attacker rewrite the log) depends on inputs the *caller asserts*, and the caller is the agent.

## Gateway: what is enforced per tool call, how policies are expressed, target scope, and what is bypassable

### Takeaway
The gateway is a ~150-line in-process Python function that really does run schema check → ordered policy → budget → handler → one audit event, and it is default-deny for unknown tools. But every security-relevant input (principal identity and role, taint, tenant) is a plain object built by the caller, there is no notion of target scope anywhere, validation is top-level-only, and nothing stops code from calling a tool handler or mutating the graph directly. A scope allowlist can be added here in roughly one rule plus one `ToolDef` field, but it only becomes a real control once the gateway is moved out of the agent's process and becomes the only holder of credentials.

### Cited Findings

Pipeline as actually coded
- [CODE] `Gateway.invoke(principal, tool_name, args, context)` runs: params hash → schema validation → policy → budget → stub credential → handler → result taint tag → audit append (`gateway/gateway.py:47-107`). The docstring lists the same seven steps and labels credential injection "stubbed" (`gateway/gateway.py:3-10`).
- [CODE] Unknown tool: schema validation is skipped (`gateway/gateway.py:58`) and the policy engine returns `unknown_tool` deny (`gateway/policy.py:93-94`). No rule matched → `default_deny` (`gateway/policy.py:99-101`).
- [CODE] Credential "injection" is the literal string `f"scoped:{tool_name}:{principal.id}"` (`gateway/gateway.py:82`). There is no secret store, no TTL, no scoping.
- [CODE] Handler exceptions are caught and returned as `status="error", reason=f"handler_error:{exc}"` (`gateway/gateway.py:86-94`): the gateway does not crash, but raw exception text flows back to the agent.

Schema validation
- [CODE] Home-made JSON-Schema subset: `required` keys, top-level per-property `type`, and `enum` only (`gateway/validation.py:3-4`, `:21-41`). No `additionalProperties`, no nested object/array item validation, no `pattern`/`maxLength`/`format`, no numeric ranges.
- [PROBE] `repo.write` with `{"repo":"../../etc","branch":"main; rm -rf /","diff":"d","force":True,"extra":{...}}` → `status=ok`. Extra and hostile arguments pass untouched.
- [CODE]+[PROBE] `compute_params_hash` is `json.dumps(args, sort_keys=True, ...)` with no `default=` (`gateway/policy.py:27-30`) and it is the first statement of `invoke` (`gateway/gateway.py:54`). Non-JSON args (e.g. a `set`) raise `TypeError` out of `invoke` with **zero** audit events, breaking the "exactly one audit event per invoke" invariant claimed at `gateway/gateway.py:10`.

How policies are expressed
- [CODE] Policies are six hard-coded Python methods in a private list, evaluated in fixed order, first decision wins (`gateway/policy.py:77-84`, `:95-98`): `taint_firewall`, `perception_computation`, `memory_provenance`, `role_scope`, `approval_gate`, `action_low_risk`. There is no policy file, DSL, versioning or reload. The module says it "mirrors the OPA/Rego policy at the Go gateway" (`gateway/policy.py:3`); neither OPA nor a Go gateway exists (`docs/rfc/15-reference-implementation-status.md:37`, `:93-95`).
- [CODE] The combinator is "first rule that returns anything wins", which means an *allow* from an early rule short-circuits later *deny* rules. It is not deny-overrides.
- [CODE] Rule content:
  - Perception and computation tools are allowed for **any** principal with `kind == "agent"`, with no role check, no rate limit, and regardless of the tool's `risk_class` or `requires_approval` (`gateway/policy.py:122-132`).
  - Memory tools: names starting `graph.write`/`vector.upsert` need a key called `provenance` to be present in args, content unchecked at this layer (`gateway/policy.py:22`, `:134-148`).
  - Role scoping exists only for tool names starting `deploy.`/`infra.` and only for the one hard-coded role string `infra_agent`; `deploy.rollback` is pre-authorized with no token (`gateway/policy.py:24`, `:150-165`).
  - Approval gate applies only to `family == "action"` with `risk_class in (high, destructive)` or `requires_approval` (`gateway/policy.py:167-197`).
  - Any agent may call any low/medium action tool (`gateway/policy.py:199-212`).
- [PROBE] Consequences of the above, all `status=ok`: a `developer` principal calling `repo.merge`; a `qa_agent` calling `notify.send`; a tool registered as `family="computation", risk_class="destructive", requires_approval=True` called from an `external_untrusted` context with no token. **Family classification is therefore the single most important trust decision in the system**: anything filed under perception/computation skips both the taint firewall and the approval gate. For a security agent, an nmap scan, an exploit attempt or `code.execute` would naturally be filed there.

Budgets
- [CODE] `BudgetGovernor` counts calls per principal id against an optional max; principals with no configured limit are unmetered (`gateway/budget.py:9-32`). `build_platform` constructs it with no limits (`plat/system.py:87`); [PROBE] `remaining("dev-7")` → `None`.
- [CODE] No time window or reset, no per-tool or per-target limit, no token/cost budget, in-memory only. The budget check runs *after* policy (`gateway/gateway.py:71-79`), which matters for approval tokens (see approval section).

Identity
- [CODE] `Principal(kind, id, role)` is a pydantic model constructed by the caller (`gateway/policy.py:47-50`); the agent runtime builds its own (`plat/agents/runtime.py:45`). The gateway performs no authentication of it.
- [PROBE] `Principal(kind="agent", id="dev-7", role="infra_agent")` calling `deploy.rollback` → `ok`. Role is self-asserted.

Audit emitted by the gateway
- [CODE] One event per allowed/denied/errored call containing actor kind/id, tool name, params **hash**, mission/task/trace ids and the caller-declared taint (`gateway/gateway.py:124-147`).
- [CODE]+[PROBE] The denial **reason** and the deciding **policy name** are computed (`gateway/policy.py:62-65`) but not written to the audit event (`gateway/gateway.py:111-122`); a denial event is just `type="policy_decision"` plus tool and hash. Handler errors are recorded as `type="tool_call"`, identical to a success (`gateway/gateway.py:89-91` vs `:102-104`; probe: `handler_error:division by zero` → audit `action.type == "tool_call"`). The log cannot distinguish "ran fine" from "blew up", or "blocked by taint firewall" from "schema violation".
- [CODE] Audit is appended *after* the handler executes (`gateway/gateway.py:87` then `:102`). There is no intent record before execution, so a crash or audit failure between the two leaves an executed action with no trace.

Target scope
- [CODE] There is no host, repo, account, path, CIDR or URL allowlist anywhere in the code (searched all packages). `CallContext` carries `tenant_id, mission_id, task_id, trace_id, taint, approval_token` (`gateway/policy.py:53-59`); `tenant_id` is used only to select an audit chain (`gateway/gateway.py:133`). Action tools take free-form `repo`/`service` strings (`plat/tools/action.py:47-54`, `:76-83`). `ToolDef` has no field describing which arguments are targets (`gateway/registry.py:13-25`).
- [DOC-ONLY] RFC 7.1 lists "blast-radius ceilings" and "OPA per-call policy" over `(principal, role, tool, resource, risk_context)` as mitigations for scope creep (`docs/rfc/07-security-governance.md:14`, `:21-22`). No `resource` concept exists in code.

Bypassability
- [CODE] The gateway is an ordinary object in the same interpreter as the agents. Handlers are plain closures held in a dict (`gateway/registry.py:25`, `:37-38`); the knowledge graph is a shared mutable object handed to both the tools and the `Platform` (`plat/system.py:82-85`); role agents hold `self.platform` (`plat/agents/roles.py:55-57`).
- [PROBE] `platform.registry.get("deploy.release").handler({...}, "cred")` → `{'released': True}` with audit delta 0. `platform.graph.add_node("evil", ..., tier="trusted")` → trusted node created with no gateway involvement.
- [CODE] The demo's own seed corpus is written with direct `add_node`/`add_edge` calls that bypass the gateway and the ontology validator (`plat/corpus.py:41-135`), and several seeded edges would fail validation, e.g. `DEPENDS_ON` Product→Repository (`plat/corpus.py:133` vs `graph/ontology/schemas/ontology-v1.yaml:140-143`) and `IMPLEMENTS` Method→Claim (`plat/corpus.py:123` vs `ontology-v1.yaml:135-138`).
- [CODE]+[PROBE] `ToolRegistry.register` silently overwrites by name (`gateway/registry.py:34-35`). Re-registering `deploy.release` as `family="computation", risk_class="low"` made it callable by a developer from a tainted context with no token. Tool definitions are unsigned and unpinned.
- [DOC-ONLY] ADR-004 says the gateway is "the only network path from agents to anything" (`docs/adr/004-mcp-gateway-chokepoint.md:11`). In code there is no network boundary at all.

### Inferences
- A scope allowlist is enforceable here with modest code: the rule signature already receives `args` (`gateway/policy.py:71`). It needs (a) a `ToolDef` field declaring target-bearing parameters and their kind (host/CIDR/URL/path/repo/account), (b) a scope rule placed first, with canonicalisation (DNS vs IP, URL parsing, path normalisation, symlinks) and (c) a deny-overrides combinator so a later allow cannot rescue an out-of-scope call. The scope document should be signed/owned by the human, not readable-writable by the agent.
- A policy-level scope check only sees *declared* arguments. A tool such as `code.execute` or a shell runner can reach anything regardless of what its args say, so scope must also be enforced below the gateway (network namespace/nftables egress rules, filesystem mounts, per-tool OS user).
- To make "single choke point" true, the gateway must be a separate process (ideally separate OS user) that alone holds tool credentials, authenticates the caller over a socket, and writes an intent record before executing. In the present layout the choke point is a convention.
- The "family" taxonomy should be replaced or augmented for security work: active scanning and exploitation are world-touching and must not inherit the perception/computation free pass.

### Gaps
- No Go gateway, OPA pack, Vault integration or MCP wire protocol exists to review; only the Python reference (`docs/rfc/15-reference-implementation-status.md:21-26`). Behaviour under real MCP transports, concurrency or load is untested.
- Whether GitHub-side settings (branch protection, default token permissions) compensate for anything could not be checked from the local checkout.

## Taint firewall (ADR-008): how taint is tracked, what resets it, what it blocks, the 3d47b97 bypass, and whether it fits a security agent

### Takeaway
There is no taint *tracking*. Taint is a two-valued field on the per-call context that defaults to `trusted` and is filled in by the caller; in the demo the script literally passes `taint="external_untrusted"` on the one call it wants blocked and `taint="trusted"` on the next. The gateway rule itself is sound and correctly ordered ahead of the approval gate, but it protects only against an agent that honestly declares itself contaminated. Taint does not propagate into the graph store, task memory, ledger, claims, session memory or the dicts passed between agents. For a security agent the model as written is simultaneously too strict (if enforced honestly, the agent cannot even send an alert or roll back after reading a log) and trivially circumvented (start a "clean" turn and carry the content across in any unlabelled channel).

### Cited Findings

How taint is represented and who sets it
- [CODE] `Taint = Literal["trusted", "external_untrusted"]` (`gateway/policy.py:19`); it lives on `CallContext.taint` with default `"trusted"` (`gateway/policy.py:58`). `AgentRuntime.call(..., taint: str = "trusted")` forwards whatever the caller passes (`plat/agents/runtime.py:125-143`). The default is fail-open.
- [CODE] `AgentRuntime.think()` computes a `turn_taint` when untrusted data is in the prompt, but only writes it into the `prompt` audit event; it is not stored on the runtime and `call()` never consults it (`plat/agents/runtime.py:107-121`).
- [CODE] The gateway tags perception results `result_taint="external_untrusted"` (`gateway/gateway.py:96-99`), but no non-test code reads `result_taint` (repo-wide search: only `gateway.py` and three test files).
- [CODE] In the scripted Developer flow: `research.search`/`research.fetch` are called with default trusted taint (`plat/agents/roles.py:215-218`); the "blocked" `repo.write` passes `taint="external_untrusted"` by hand (`roles.py:228-233`); the "clean turn" commit passes `taint="trusted"` by hand (`roles.py:249-254`).
- [PROBE] `research.fetch` (result_taint `external_untrusted`) followed immediately by `repo.write` whose `diff` is the fetched text, both with default context → `repo.write status: ok`.

Granularity and reset
- [CODE] Granularity is per call. There is no per-turn, per-agent, per-session or per-value state. "Turn" is not an object in the code.
- [CODE] Nothing resets taint because nothing holds it. `fresh_context()` only clears the `hypotheses` and `attempts` lists and explicitly keeps the ledger and claims (`plat/agents/runtime.py:56-62`).

What the rule blocks
- [CODE] When `context.taint == "external_untrusted"`: every `family == "action"` tool is denied, and any memory-family call whose args contain `"tier": "trusted"` at any depth is denied (`gateway/policy.py:105-120`). It is the first rule, so a valid approval token cannot rescue a tainted action (`gateway/policy.py:78`; test `backend/gateway/tests/test_gateway_policy.py:34`).
- [CODE] Because it is first and family-wide, it also blocks `notify.send` and the pre-authorized `deploy.rollback` under taint (`plat/tools/action.py:65-72`, `:86-90`).
- [CODE] Still allowed under taint: all perception and computation tools including `code.execute` with `network="package_registries"` (`gateway/policy.py:122-132`; `plat/tools/computation.py:67-77`; used that way at `plat/agents/roles.py:235-240`), `graph.query`, `focal.extract`, and staging-tier `graph.write`.

The 3d47b97 bypass and its fix
- [CODE] Before the fix the rule was `args.get("tier") == "trusted"` (top-level key only). The platform's `graph.write` handler takes the tier from each node spec, `tier=nspec.get("tier", "staging")` (`plat/tools/memory.py:44`), so an untrusted turn could omit the top-level hint and put `"tier": "trusted"` inside the node payload and mint a trusted node (commit message of `3d47b97`, "Security (verified exploitable, now closed)").
- [CODE] Fix: recursive scan `_requests_trusted_tier` over dicts and lists (`gateway/policy.py:33-44`), used at `gateway/policy.py:116`. Regression tests: `backend/gateway/tests/test_gateway_policy.py:66` and `platform/tests/test_platform_tools.py:83`.
- [CODE] The fix is still a deny-list keyed on one literal key/value spelling. It holds for today's `graph.write` because the handler reads exactly that key and pydantic's `Tier` literal rejects other spellings (`onto/models.py:13`), but any future memory tool that expresses trust differently (`trust_level`, `promote: true`, a separate `graph.promote`) would not be covered. Handlers are called as `handler(args, credential)` (`gateway/gateway.py:87`): the context taint is never passed down, so the store cannot enforce or record it itself.

Holes that remain after the fix (all verified)
- [PROBE] Self-declared trusted turn after reading untrusted content writes a `tier="trusted"` Claim node whose `statement` is the fetched paper text → `ok`, tier `trusted`. `provenance.taint` is also agent-supplied (`plat/agents/roles.py:84-87`), and the validator's "trusted tier requires provenance taint == trusted" check (`onto/validate.py:31-36`) just compares two caller-supplied fields.
- [PROBE] A tainted, staging-tier `graph.write` reusing the id of an existing trusted node replaced it: `method-lhce` went from `('trusted', 'Predicts cell cycle-life ...')` to `('staging', 'IGNORE PREVIOUS')`. Cause: `self.nodes[id] = node` is an unconditional overwrite (`focal/graph.py:73`) and the handler never checks for an existing node (`plat/tools/memory.py:56-67`). Untrusted content can delete or demote trusted knowledge.
- [PROBE] A tainted turn added an edge between two existing trusted nodes → `ok`, and an edge whose declared endpoint types were lies → `ok`. Edges have no tier (`onto/models.py:78-86`, `focal/graph.py:30-37`) and declared endpoint types are checked only against nodes in the same batch, never the stored graph (`onto/validate.py:94-103`). This is a direct lever on PPR ranking.
- [PROBE] `focal.extract` with `include_staging=True`: the brief's own `taint` field is `external_untrusted` and the poison text is in `rendered_context`, but the gateway's `result_taint` is `trusted`, because the tool is memory-family and the gateway copies the caller's context taint (`gateway/gateway.py:97-99`).
- [PROBE] The prompt fence is not escaped: untrusted content containing the closing marker `<<<END_EXTERNAL_DATA>>>` terminates the fence early and the following attacker text sits outside it (`mem/assembler.py:28-29`, `:55-58`). The only hard assembler rule is that an untrusted segment cannot have kind `system` (`mem/assembler.py:68-72`).

Propagation through memory, graph and inter-agent paths
- [CODE] Graph: the stored `Node` has `tier` but no taint or provenance field (`focal/graph.py:15-27`); `graph.write` validates provenance and then drops it (`plat/tools/memory.py:56-67`). A focal brief's taint is purely `"external_untrusted" if include_staging else "trusted"` (`focal/extract.py:376-378`), not derived from node provenance. Trusted-tier node summaries are rendered raw into the prompt and treated as trusted (`focal/extract.py:333-344`; `plat/agents/runtime.py:92-98`).
- [CODE] Task memory: `TaskMemory`, `ToolLedgerEntry` and `Claim` have no taint field (`mem/models.py:24-49`). `SessionMemoryStore` values carry no taint (`mem/store.py:52-63`) and the store is not wired into the platform (only defined and exported).
- [CODE] Inter-agent: there is no messaging layer. The orchestrator passes Python dicts from one role's return value to the next (`plat/mission/orchestrator.py:172-184`, `:219-240`). The Developer's `claims_sheet`, authored after its tainted turn, is placed into the H4 human approval evidence with no taint mark (`orchestrator.py:253`). The status doc confirms "ACP envelope is an informal dict" (`docs/rfc/15-reference-implementation-status.md:41`).
- [DOC-ONLY] ADR-008 states taint "propagates from ingestion through graph nodes, focal-graph rendering, into each assembled prompt" and that the gateway "inspects the taint of the agent's current context per turn" (`docs/adr/008-taint-tool-firewall.md:12-15`). Neither is implemented; ingestion does not exist.
- [DOC-ONLY] The intended bridge from untrusted to actionable is a "laundering step" via promotion to trusted tier by corroboration from ≥2 independent sources or human curation (`docs/adr/008-taint-tool-firewall.md:20`; `docs/rfc/04-knowledge-memory.md:145-148`). No promotion code exists (search for "promot" in Python finds only a comment at `plat/corpus.py:50`). "Egress only via allowlisting proxy" (`docs/adr/008-taint-tool-firewall.md:16`) has no implementation either.

What the demo's "forensic proof" actually proves
- [CODE] "Could the paper have injected anything? No ... 0 Action calls succeeded under untrusted taint (verified from the log)" is computed by filtering audit events on the *caller-declared* taint (`plat/mission/orchestrator.py:332-348`). Since the script declares the commit call trusted, the statement is true by construction and says nothing about information flow.

### Inferences
- Does "tainted ⇒ no actions this turn" make a security agent unable to do its job? If a real runtime latched taint whenever a perception result entered context (the obvious honest implementation of ADR-008), then yes for single-turn work: every triage starts by reading attacker-controllable data (auth logs, HTTP bodies, file contents, package metadata), after which the agent could not notify, isolate, block, patch or roll back. The security use case inverts the research assumption that reading and acting can be separated in time.
- Is it trivially circumvented? As coded, yes, in three independent ways: (1) the agent simply does not declare taint; (2) a new call context is "clean" by default; (3) content crosses into the clean context through unlabelled carriers: task memory, claims, ledger-adjacent dicts, staging nodes that overwrite trusted ids, edges, or a self-declared trusted write. The demo's own happy path is method (2): the artifact built under taint is committed one call later.
- What would have to change, in order of importance:
  1. Taint must be set by the gateway/runtime, not the caller: latch per session on any perception result, persist it, and make "trusted" something that must be earned.
  2. Replace binary block with a matrix over (taint, tool, target-in-scope, reversibility). Under taint allow a small set of pre-approved, reversible, in-scope containment playbooks and fixed-template alerts; require a human token for everything else. Blocking `notify.send` under taint is the wrong default for a detection system.
  3. Add an explicit declassification step instead of "new turn": a quarantined reader extracts typed fields (IP, hash, CVE id, PID, path) validated by schema, and only those typed values reach the privileged planner (dual-LLM / capability pattern). Free text never crosses.
  4. Carry labels on stored values: provenance and taint on graph nodes and edges, memory records, ledger entries and inter-agent messages; forbid overwrite of trusted nodes by lower-trust writers.
  5. Escape or randomise the fence delimiter per prompt.

### Gaps
- No LLM is connected, so there is no empirical data on how any model behaves with the fence or under injection; the RFC's "red-team suite" (`docs/rfc/07-security-governance.md:86`) does not exist.
- Injection sentinels and output scanning (`docs/rfc/07-security-governance.md:89-90`) have no code; nothing to assess.

## Approval tokens (ADR-009): signature scheme, key handling, what is bound, single-use, state, replay/TOCTOU, what the human sees

### Takeaway
The cryptographic core is fine: Ed25519/EdDSA JWTs with a pinned algorithm, required `exp/iat/jti`, 15-minute default TTL and a consumed-`jti` set. The weaknesses are in binding and context. Verification checks only signature, expiry, `params_hash` and `jti`; it does not check the tool, the principal, the tenant or the checkpoint, and the hash covers the args but not the tool name, so a token approved for one tool works on any other approval-gated tool called with the same args. The signing key is generated inside the agent's process, consumed-`jti` state is in memory, approver identity is an unauthenticated string, and the human is shown a summary assembled by the agent side rather than the bytes being hashed.

### Cited Findings

Scheme and keys
- [CODE] PyJWT with `algorithm="EdDSA"` over an Ed25519 key (`approval/service.py:10-11`, `:21`, `:133`). Verification pins `algorithms=["EdDSA"]` and requires `jti`, `exp`, `iat` (`approval/service.py:136-146`), which rules out `alg=none` and algorithm-confusion attacks. Tests cover tampering and wrong-key (`backend/approval/tests/test_service.py`, classes `TestTampering`, `TestExpiry`).
- [CODE] `keys.py` only generates, PEM-serialises (unencrypted, `NoEncryption()`) and loads keys (`approval/keys.py:14-45`). There is no KMS/HSM, no file permission handling, no rotation and no `kid`.
- [CODE] The private key is generated in-process at platform start and held by `ApprovalService` in the same interpreter as the agents and gateway (`plat/system.py:79-80`; `approval/service.py:33`). The FastAPI app builds a brand-new platform, hence a new key, per mission (`plat/app.py:57`).
- [DOC-ONLY] "Key management for the signing key is now critical-path (KMS-backed, rotated)" (`docs/adr/009-approval-tokens.md:21`).

What is bound
- [CODE] Claims issued: `jti, checkpoint, action_type, params_hash, approver, tenant_id, iat, exp, single_use` (`approval/service.py:120-133`). Not present: tool name, calling principal/agent, mission id, request id, `subject_id` (it is on the request, `approval/service.py:59`, but not copied into the token), `aud`, `iss`, `nbf`.
- [CODE] `verify(token, params_hash)` checks signature/expiry, then `params_hash` equality, then `jti` not yet consumed (`approval/service.py:135-162`). The gateway's injected verifier has exactly that two-argument shape (`gateway/policy.py:68-69`, `:188`); `checkpoint`, `action_type` and `tenant_id` in the token are never compared with the call.
- [CODE] `params_hash` is SHA-256 over canonical JSON of the args only; the tool name is not part of it (`gateway/policy.py:27-30`).
- [PROBE] A token created with `action_type="deploy"`, checkpoint H5, for args `{"service":"svc-pricing","image_digest":"sha256:aa"}` was accepted on a different tool, `deploy.destroy` (`risk_class="destructive"`, `requires_approval=True`), called with the same args → `status=ok`, handler ran.

Single use, state and replay
- [CODE] Single-use is an in-memory `set` of consumed `jti` values under a lock (`approval/service.py:37`, `:151-155`); it is never pruned and never persisted. Pending requests live in an in-memory dict (`approval/service.py:36`).
- [PROBE] Replay across restart: a token consumed on service instance 1 verified as valid again on a second `ApprovalService` constructed with the same key. Any deployment that persists the key but not the `jti` set reopens replay for the remaining TTL.
- [CODE]+[PROBE] The token is consumed during policy evaluation, before the budget check and before the handler runs (`gateway/gateway.py:71-79`, `:87`). With the infra agent's budget at 0, the first `deploy.release` returned `budget_exhausted` and the retry with the same token returned `approval_invalid:token_already_used`. A handler exception burns the token the same way. There is no link between "token consumed" and "action completed".
- [CODE] A params mismatch does not consume the token (`approval/service.py:148-149` precedes `:151`; test `backend/approval/tests/test_service.py:67`).
- [CODE] Pending requests never expire: the `"expired"` status literal exists (`approval/models.py:37`) but no code sets it. A stale request can be approved at any later time and yields a fresh 15-minute token.
- [CODE] The REST `POST /v1/approvals/verify` endpoint calls the consuming `verify` (`approval/app.py:56-58`); anyone who can reach it with a token can burn it.

TOCTOU
- [CODE] The hash binds argument *values*, not world state. Deploy binds an immutable image digest (`plat/mission/orchestrator.py:272-283`), which is the right pattern. The H4 merge hash is over `{"branch", "commit"}` (`orchestrator.py:251`), but the subsequent `repo.merge` call sends `{"repo", "branch"}` with no token and no commit (`orchestrator.py:255-258`), so what was approved and what is executed are not cryptographically connected at all.

Which gates are actually enforced by a token
- [CODE] Only `deploy.release` is registered `requires_approval=True` (`plat/tools/action.py:73-85`) and only the H5 token is passed to a tool call (`plat/mission/orchestrator.py:277-284`; `plat/agents/roles.py:317-321`). H1, H2 and H4 produce tokens that are discarded (`orchestrator.py:187-192`, `:204-211`, `:248-254`); those gates are enforced solely by the orchestrator's statement order. `repo.merge` is `risk_class="medium"` with no approval flag (`plat/tools/action.py:57-64`) and any agent can call it at the gateway (probe above).

Approver identity and dual control
- [CODE] `ApprovalDecision.approver_id` is a free string (`approval/models.py:17-22`). Neither the service nor its REST app authenticates anyone (`approval/app.py:40-58`). [PROBE] Via the REST app, an anonymous client created a request and approved it as `"dana"` and received a token.
- [CODE] Dual control means two different strings (`approval/service.py:99-114`); [PROBE] `"alice"` then `"alice2"` issues the token. It is not wired into the orchestrator (`plat/mission/orchestrator.py:91-95`).
- [CODE] In-process, role agents hold `self.platform` and therefore `platform.approval` (`plat/agents/roles.py:55-57`; `plat/system.py:35`); nothing prevents agent code from calling `create_request`/`decide` itself. RFC 7.4's "agents: no approval-granting ability ever" (`docs/rfc/07-security-governance.md:70`) is not enforced.
- [CODE] Destructive requests need an exact typed-consequence string match; a mismatch permanently rejects the request (`approval/service.py:88-97`).

What the human sees
- [CODE] The approval service receives only `params_hash`, never the params (`approval/service.py:40-53`), plus a requester-supplied `risk_score` and free-form `evidence_bundle`. The approver callback receives a `GateContext` with `checkpoint, title, subject_id, risk_score, evidence, destructive, required_consequence` (`plat/types.py:52-65`); it does not include the hash or the raw arguments. Evidence is assembled by the orchestrator from agent outputs (`plat/mission/orchestrator.py:191`, `:209-210`, `:253`, `:282`). Nothing guarantees that what is displayed corresponds to what is hashed.
- [CODE] No human interface exists. Approvers are pure functions that auto-approve (`plat/mission/approvers.py:36-56`); the status doc lists "Approval inbox UI" as deferred (`docs/rfc/15-reference-implementation-status.md:36`).
- [CODE] The audit trail records an `approval` event with `tool="H5:approved"`, the approver string and the params hash (`plat/mission/orchestrator.py:131-144`), written by the orchestrator, not by the approval service. Neither the token `jti` nor a token hash is recorded, and the gateway's `tool_call` event does not reference the token (`gateway/gateway.py:139`). ADR-009's "the token hash in the audit chain is the human-oversight evidence" (`docs/adr/009-approval-tokens.md:18`) is not implemented.

### Inferences
- For a security agent the token should bind at least: tool name and version, canonical args hash, resolved target identity (host id / repo@commit / account id), requesting principal, session or incident id, scope-document hash, `nbf/exp`, and a nonce; the gateway must verify every one of them against the live call. Cross-tool reuse is the most serious present flaw because security tooling has many tools with the same argument shape (`{"host": ...}`).
- Consumption should be two-phase (reserve on verify, commit on handler success, release on pre-execution failure) and the `jti` store must be durable and outlive the key.
- The signer has to live outside anything the agent can influence: separate OS user or separate device, with approval delivered over a channel the box cannot forge (hardware key/WebAuthn, or a phone app holding the key). On a single VM where the agent may be compromised, an in-VM approval service only proves the VM approved itself.
- "What you see is what you sign": the approval service should receive the full canonical request, render it itself, and hash exactly what it rendered. Agent-authored text shown to the approver must be marked as untrusted.

### Gaps
- No UI, chat-ops path or notification channel exists, so approval ergonomics and fatigue controls (`docs/rfc/07-security-governance.md:125`) cannot be evaluated.
- Behaviour under clock skew or PyJWT leeway settings is not tested; default leeway (0) is used implicitly.

## Audit chain: construction, contents, tamper-evidence versus tamper-resistance

### Takeaway
A correct SHA-256 hash chain per tenant with a verifier and a Merkle-root helper, held in a Python list. It detects an in-place edit that does not recompute the suffix, and nothing more: there is no key, signature, persistence or external anchor, so anyone with write access to the process (or, in future, the file) can truncate the tail or rebuild the whole chain and `verify_chain` returns valid. Events are also thin: no outcome, no denial reason, no arguments or results, and the "who" and "taint" fields are whatever the caller said.

### Cited Findings

Construction
- [CODE] Event hash = SHA-256 of canonical JSON (sorted keys, no whitespace) of every field except `event_hash`, which includes `seq`, `prev_hash`, `ts`, actor, action, context (`audit/chain.py:16-32`; `audit/store.py:59-69`). Genesis `prev_hash` is 64 zeros (`audit/chain.py:13`).
- [CODE] `InMemoryAuditStore` keeps `Dict[tenant, List[AuditEvent]]`, assigning `seq` and `prev_hash` under one lock (`audit/store.py:39-71`); a concurrency test exists (`backend/audit/tests/test_store.py`, `test_concurrent_appends_yield_valid_chain`).
- [CODE] `verify_chain` checks strictly increasing `seq`, recomputed hash, and link to predecessor (`audit/chain.py:42-69`). It does not require contiguity or that the first `seq` is 1, but it does require the first event's `prev_hash` to be genesis, so [PROBE] verifying a segment starting at `from_seq=2` fails with `broken_link`: segment verification against a trusted checkpoint is not supported.
- [CODE] `segment_merkle_root` builds a duplicate-last-node Merkle tree over event hashes with no leaf/node domain separation (`audit/chain.py:72-84`). It is exposed by one REST endpoint (`audit/app.py:65-74`) and called by nothing else; no sealing, scheduling or anchoring exists.

What is recorded and what is not
- [CODE] Fields: `event_id, seq, tenant_id, actor{kind,id,on_behalf_of_mission}, action{type,tool,params_hash,content_ref}, context{mission_id,task_id,trace_id,taint}, ts, prev_hash, event_hash` (`audit/models.py:10-55`).
- [CODE] Not recorded: decision reason or policy name, success/error outcome, result or result hash, the arguments themselves (hash only, with no content store to resolve it), approval token id, tool version, target. Prompt events store only a prompt hash in `content_ref` (`plat/agents/runtime.py:113-120`); the prompt text is kept nowhere, so the "replay" claim in the walkthrough (`examples/mission-walkthrough.md`, closing section) is not achievable from the log.
- [CODE] `ts` can be supplied by the caller (`audit/store.py:50-53`; test `backend/audit/tests/test_store.py:29`). Actor and taint are caller-supplied objects.
- [CODE] Not everything is audited: the approval service itself writes no audit events (the orchestrator does, `plat/mission/orchestrator.py:122-128`); direct graph mutations and handler internals are invisible; `Platform.audit_event` lets any in-process code append arbitrary events (`plat/system.py:46-66`).

Tamper-evidence versus tamper-resistance
- [PROBE] On a 6-event chain ending in a malicious `repo.write`: removing the last event → `verify_chain` valid with length 5. Rewriting event 2's tool and actor and recomputing every hash forward → valid.
- [CODE] Tests cover a tampered middle event and a relink attempt detected at the next event (`backend/audit/tests/test_chain.py:53`, `:65`); there is no test for truncation or full recomputation, because the design cannot detect them.
- [PROBE] The audit REST app has no authentication: an anonymous `POST /v1/audit/events` with `actor={"kind":"human","id":"dana"}`, `action={"type":"approval","tool":"H5:approved"}` → 201, seq 1. Forged human-approval evidence is one request away.
- [PROBE] The platform app's `GET /audit/verify` verifies the long-lived `info_platform`, while each mission runs on a fresh platform (`plat/app.py:30`, `:57`, `:65-69`); after a completed 28-event mission it returned `{'length': 0, 'valid': True}`. The endpoint is vacuous.
- [DOC-ONLY] "append-only Postgres staging → hourly sealed segments to GCS with bucket lock (WORM); segment Merkle roots anchored to an external timestamping service. Tampering is detectable; deletion is impossible within retention" (`docs/rfc/07-security-governance.md:108`). Status doc lists WORM sealing and the seal cron as deferred (`docs/rfc/15-reference-implementation-status.md:35`).

### Inferences
- If the attacker owns the box, the present chain offers no protection: no secret is needed to recompute it and the head hash is stored nowhere else. For a self-hosted security agent this is the component whose threat model changes most, because "attacker gets root on the VM the agent lives on" is the scenario the log exists for.
- Minimum viable hardening for one VM: (1) append-only persistence written by a separate OS user (or `chattr +a`, or journald with forward-secure sealing); (2) sign each event or each checkpoint with a key the agent user cannot read; (3) ship the head hash (or every event) off-box continuously: a second machine, an object-lock bucket, a transparency log, or even a timestamped message to the owner's phone; (4) verify against the last externally held head, not genesis. Forward-secure MACs (key ratcheting) give truncation resistance for the period before compromise even without a network.
- Event schema needs: outcome, decision and policy version, result hash, target, token `jti`, tool version, monotonic clock plus wall clock, and a pre-execution intent record.

### Gaps
- Throughput, on-disk format and crash consistency are unaddressed because there is no persistent store (the Protocol at `audit/store.py:14-36` is the only seam).
- No retention, rotation or redaction design in code; the audit log of a security agent will contain sensitive material (paths, hostnames, possibly secrets in args if args are ever stored).

## Risk score → autonomy level: computation, tiers, who supplies inputs

### Takeaway
The risk score is a four-term linear formula evaluated inside the agent-side role class, on numbers returned by a stub tool and a constant the agent itself supplies, and the resulting autonomy mode is displayed but never changes control flow. It is decoration today. The thing that actually gates behaviour is the static `risk_class`/`requires_approval` on each registered tool.

### Cited Findings
- [CODE] `R = 0.45·min(symbols/40,1) + 0.35·min(services/4,1) + 0.20·untested_fraction + novelty`, clamped to 1 and rounded; `R < 0.30` → `autonomous`, `< 0.65` → `supervised`, else `manual` (`plat/agents/roles.py:23-49`).
- [CODE] Inputs: `blast_radius` comes from the `blast.analyze` tool, which returns constants (`plat/tools/computation.py:22-32`); `novelty=0.10` is hard-coded by the Head Engineer role when it calls the function (`plat/agents/roles.py:186-189`). The docstring says reversibility is "folded in by the orchestrator" (`roles.py:30-31`); no code does so.
- [CODE] The computation runs in `HeadEngineer.plan`, i.e. inside the agent being governed (`plat/agents/roles.py:174-202`). With an LLM-driven agent every input (which repo to analyse, the novelty value, even whether to call the analyser) would be agent-chosen.
- [CODE] The mode is only stored and printed: `orchestrator.py:202`, `:209`, `:214`, `:253`; `plat/demo.py:42`. No branch anywhere depends on it; all four gates run in every mode. Approval-request `risk_score` values are partly literals (`0.2` at `orchestrator.py:190`; fallback `0.34` at `:281`).
- [CODE] Demo output is `R=0.36 (supervised)`; the walkthrough document says 0.34 (`examples/mission-walkthrough.md`, Day 1–2 step 6).
- [DOC-ONLY] RFC 1 defines four tiers (0–0.2 autonomous, 0.2–0.5 supervised, 0.5–0.8 collaborative, 0.8–1.0 human-led) (`docs/rfc/01-philosophy.md:116-124`); RFC 5 gives a different formula including `data_sensitivity` and weights "calibrated against historical defect escapes" (`docs/rfc/05-ase-workflow.md:93`). Code has three tiers, different thresholds, no data-sensitivity term and no calibration.
- [CODE] The enforced lever is per-tool: `risk_class` and `requires_approval` on `ToolDef` (`gateway/registry.py:10`, `:21-23`) consumed by the approval gate (`gateway/policy.py:172-174`). These are set by whoever registers the tool and can be overwritten by re-registration (see gateway section).
- [CODE] The companion "claims sheet vs blast radius" check compares agent-declared constants (`plat/agents/roles.py:268`) against the stub analyser's constants (`plat/mission/orchestrator.py:294-310`); the docstring concedes the real diff comparison is not implemented (`orchestrator.py:300-302`).

### Inferences
- Can the agent influence its own risk score? Yes, completely, in the current structure. For a security agent, risk must be computed by the gateway from facts the agent does not control: asset criticality from the owner-maintained inventory, action class and reversibility from the signed tool manifest, scope membership, current taint, time of day/change window, and recent error rate.
- The software-change inputs (symbols, services, untested fraction) do not transfer. A security analogue would be: target criticality × action intrusiveness (read / active probe / config change / process kill / network isolation / credential rotation / exploit) × reversibility (has a tested undo) × confidence in the finding.
- The mode needs to do something: e.g. `autonomous` = execute and notify, `supervised` = execute reversible playbooks then require confirmation to keep the change, `manual` = token required before execution.

### Gaps
- No defect-escape or catch-rate measurement exists, so the RFC's "calibrated trust dial" (`docs/rfc/01-philosophy.md:133`) has no data source.

## Graph, focal graph, and memory with grounded-claim checks: what they do, research-specificity, fit for a security graph, poisoning exposure

### Takeaway
The ontology *mechanism* (YAML-declared node and edge types, required metadata keys, endpoint-type constraints, mandatory provenance) is domain-neutral and reusable; the ontology *content*, the provenance source enum, the focal purpose profiles and the corpus are entirely research-to-product and would be replaced. The in-memory graph store itself is too weak to be an evidence store (no provenance kept, silent overwrite, no history). The grounded-claim check is a referential-integrity check ("this claim cites some successful tool call") with no connection between the claim's content and the evidence; it is the right hook for "a finding needs evidence" but needs an evidence store the agent cannot write and type rules about which evidence supports which finding. Memory-poisoning exposure is high wherever data is stored: node overwrite, unlabelled edges, lesson overwrite by word-overlap, and trusted-tier text rendered unfenced into prompts.

### Cited Findings

Ontology
- [CODE] `ontology-v1.yaml`: 4 layers (`research, code, market, platform`), 24 node types, 13 relation types (`graph/ontology/schemas/ontology-v1.yaml:3-7`, `:9-112`, `:114-180`). Examples: `ResearchPaper, Claim, Method, Dataset, Metric, Author, Institution; Repository, CodeBlock, Interface, Dependency, TestCase, SoftwareArtifact; Company, Product, MarketSignal, Segment, Need; Opportunity, Hypothesis, ARS, Task, DeploymentRecord, AgentEpisode`; relations `CITES, IMPROVES_ON, CONTRADICTS, EVALUATED_ON, IMPLEMENTS, DEPENDS_ON, COMPETES_WITH, SIGNALS_DEMAND_FOR, ADDRESSES, IMPLEMENTABLE_AS, SAME_AS_CANDIDATE, AUTHORED_BY, AFFILIATED_WITH`.
- [CODE] Loader checks duplicates, layer membership, relation endpoints exist, cross-layer flag consistency (`onto/loader.py:73-93`). Instance validation: known type, required metadata **keys present** (values and types unchecked), provenance present, confidence in [0,1], trusted tier requires `provenance.taint == "trusted"`, edge endpoint types allowed, weight in [0,1] (`onto/validate.py:10-74`); batch consistency only within the batch (`onto/validate.py:77-105`).
- [CODE] `Provenance.source_type` is a Python literal `paper | market_feed | telemetry | agent_inference | human`, hard-coded outside the YAML (`onto/models.py:11`, `:60-65`; duplicated in `onto/export.py:13-15`).
- [CODE] Exporters emit Neo4j constraint DDL and a JSON Schema (`onto/export.py:31-40`); no Neo4j is used.

Graph store
- [CODE] `InMemoryKnowledgeGraph`: dict of nodes, list of edges, forward and reverse adjacency (`focal/graph.py:40-104`). `Node` fields: `id, type, layer, name, summary, confidence, tier, embedding, created_at_days_ago` (`focal/graph.py:15-27`): no provenance, no taint, no timestamps (age is a float "days ago"), no version. `add_node` overwrites (`focal/graph.py:73`); edges are append-only with no dedup, no delete, no deprecate. Nothing is persisted.

Focal graph
- [CODE] `focal_extract` pipeline: seeds (caller ids ∪ cosine top-8 over embeddings) → personalized PageRank by local push, traversing edges in both directions with purpose-specific edge-type multipliers → relevance = α·PPR + β·cosine + γ·confidence + δ·recency → keep nodes within 3 hops of a seed up to `max_nodes` → per-node `why_included` path and a `coverage_note` listing what was pruned → text rendering trimmed to a character budget (`focal/extract.py:1-11`, `:122-389`; `focal/ppr.py:38-118`).
- [CODE] Staging-tier nodes are excluded unless `include_staging=True` (`focal/extract.py:141-142`, `:190-197`); requesting staging marks the whole brief untrusted (`focal/extract.py:376-378`). This is the only poisoning defence in retrieval, and it depends on `tier`, which the previous section shows is agent-settable.
- [CODE] Five purpose profiles, all research/product-shaped: `opportunity_mining, code_task_brief, spec_drafting, review, explain` (`focal/purposes.py:23-100`).
- [CODE] `confidence` is taken from the writer's args (`plat/tools/memory.py:43`) and feeds relevance directly (`focal/extract.py:209-214`); edge additions shift PPR mass. Rendering inserts node `summary` text verbatim (`focal/extract.py:333-344`).
- [DOC-ONLY] ADR-007 specifies "Steiner-tree pruning" (`docs/adr/007-focal-graph.md:13`); the code does a greedy hop-bounded keep (`focal/extract.py:244-255`), which the status doc describes accurately (`docs/rfc/15-reference-implementation-status.md:39`).

Memory package
- [CODE] `PromptAssembler`: fixed segment order (`system, ars, focal, exemplars, task_memory, tool_results`), per-kind and total token budgets (tokens estimated as `len/4`, `mem/tokens.py:6-8`), deterministic eviction, fencing of untrusted segments, prompt SHA-256 (`mem/assembler.py:18-25`, `:61-164`). Fence weakness noted above.
- [CODE] Grounded claims: `validate_claims` returns a violation if a claim has no `evidence_ledger_id`, cites an unknown ledger id, or cites an entry whose `result_status != "ok"` (`mem/claims.py:12-34`). That is the entire check.
- [CODE] A `ToolLedgerEntry` holds `ledger_id, tool, params_hash, result_status, summary, seq` (`mem/models.py:24-32`); `summary` is the denial reason or the string `"ok"` truncated to 120 chars (`plat/agents/runtime.py:152`). There is no result content or result hash.
- [CODE] The ledger and claims are lists on a `TaskMemory` owned by the agent's own runtime (`plat/agents/runtime.py:47`, `:53-54`, `:145-155`); the role code appends claims and picks which ledger id to cite (`plat/agents/roles.py:258-266`). The orchestrator runs the verifier afterwards (`plat/mission/orchestrator.py:222-225`).
- [PROBE] A claim "Host 10.0.0.5 is fully patched and no malware present." citing a successful `research.search` ledger entry → `violations: []`.
- [DOC-ONLY] RFC B.4 says "verification makes [fabrication] non-viable" (`docs/rfc/14-agent-prompting-standards.md:55-58`). The implemented check makes *uncited* claims non-viable, not *unsupported* ones.
- [CODE] `LessonStore`: lessons require a non-empty `rationale`; if a new lesson's `summary_line` has word-set Jaccard > 0.6 with an existing one, the existing record's summary, body, kind and rationale are overwritten in place; lessons are deprecated rather than deleted (`mem/consolidation.py:12-21`, `:44-73`). `LessonRecord` has no author, provenance, taint or timestamp. Not wired into the platform.
- [CODE] `SessionMemoryStore`: TTL key/value with JSON checkpoint/restore; restore rebuilds only a whitelist of five pydantic models (no pickle) but accepts any snapshot dict with no integrity check (`mem/store.py:22-49`, `:92-109`). Not wired into the platform.

### Inferences
- Could it hold a security graph? The validator and loader can, after a YAML rewrite: layers such as `asset, identity, vulnerability, detection, incident`; nodes `Host, Service, Process, Account, Credential, NetworkSegment, Repository, Pipeline, Dependency, Vulnerability, Technique (ATT&CK id), Detection, Control, Finding, Evidence, Incident, Remediation`; edges `RUNS_ON, EXPOSES, CAN_REACH, AUTHENTICATES_AS, DEPENDS_ON, AFFECTED_BY, EVIDENCED_BY, USES_TECHNIQUE, DETECTED_BY, MITIGATED_BY, REMEDIATES`. Reusable as-is from v1: `Repository, Dependency, SoftwareArtifact, DeploymentRecord, Task, AgentEpisode, Claim, Hypothesis, DEPENDS_ON, SAME_AS_CANDIDATE`. Required code changes: move `SourceType` into the YAML (sensor, scanner, log, human, agent_inference, threat_feed), rewrite `purposes.py` profiles (triage, attack-path, remediation-brief, report), replace the corpus.
- Could the validator enforce "a finding needs evidence"? Not today: it validates each node and edge independently and cannot express "a `Finding` must have ≥1 outgoing `EVIDENCED_BY` edge to an `Evidence` node" or value-level constraints (`onto/validate.py:17` checks key presence only). It needs cardinality rules and value typing. The claims verifier supplies the other half once (a) the ledger is written by the gateway, not the agent runtime, (b) entries carry a content hash of the result stored in an immutable evidence store, and (c) a table maps finding classes to acceptable evidence-producing tools (a "port open" finding must cite a scanner result for that host, not any successful call).
- Focal extraction is plausibly useful as "everything relevant around host X for this alert, within a token budget, with reasons", but bidirectional PPR is a relevance heuristic, not an attack-path or reachability engine; it is the lowest-priority component to carry over.
- Memory-poisoning exposure, ranked: (1) trusted-tier reachable by self-declaration, after which content is injected unfenced into every future brief; (2) node overwrite by id from a tainted write; (3) edge insertion with no tier and unchecked endpoint types; (4) agent-supplied `confidence` steering ranking; (5) `LessonStore` overwrite by 60% word overlap with no provenance (dormant but dangerous if wired to a model); (6) no history, so poisoning cannot be rolled back or even detected after the fact.

### Gaps
- No ingestion, extraction, entity resolution, vector search or promotion pipeline exists (`docs/rfc/15-reference-implementation-status.md:96-97`), so the path by which sensor data would enter the graph is undesigned for the new use case.
- Retrieval quality is unmeasured; ADR-007's benchmark gate (`docs/adr/007-focal-graph.md:21`) was not run. Graph size in the demo is 11 seeded nodes (14 after the mission).

## Orchestrator, approval gates, tools, system.py, app.py, demo.py: real versus stubbed; LLM, persistence, isolation, authn/authz, secrets, egress, sandboxing

### Takeaway
The "agent" is a script. There is no LLM call anywhere; prompts are assembled, hashed, and thrown away, and every agent output is a hard-coded literal. All 17 tools are stand-ins (only the three memory tools do real work, against the in-memory graph). The orchestrator is a straight-line function with scripted auto-approvers. There is no persistence, no process isolation, no authentication or authorization, no secrets handling, no egress control, no sandbox and no kill switch. `system.py` (a clean composition root) and the gate helper pattern are the reusable parts.

### Cited Findings
- [CODE] No LLM: "These are not LLM calls — they are scripted behaviors" (`plat/agents/roles.py:3-6`). `think()` builds and hashes a prompt and returns it (`plat/agents/runtime.py:112-121`); callers discard the return value (e.g. `roles.py:74-78`, `:123-127`). Outputs are literals: opportunity id (`roles.py:80`), the ARS (`roles.py:129-141`), task DAG (`roles.py:190-194`), declared scope (`roles.py:268`), QA "dissent" string (`roles.py:301`). A repo-wide search for LLM SDKs, `httpx`/`requests` use, `subprocess`, sockets or sqlite in non-test code found nothing (`httpx` is in `requirements.txt:6` only for FastAPI's test client).
- [CODE] Orchestrator: six stage methods called in order with a single `try/except MissionAborted` (`plat/mission/orchestrator.py:154-169`). No state persistence or resume, no retry, no timeout, no concurrency, no scheduling. It describes itself as "the Temporal-workflow stand-in" (`orchestrator.py:1`).
- [CODE] Approvers: `scripted_approver`, `auto_approver`, `rejecting_approver` are pure functions (`plat/mission/approvers.py:36-56`). No path exists for a real human to approve.
- [CODE] Tools (17, `plat/tools/__init__.py:22-32`):
  - Perception (3): `research.search`, `research.fetch`, `repo.read` read module-level dict constants (`plat/tools/perception.py:16-40`, `:44-64`).
  - Computation (6): `ast.analyze`, `deps.graph`, `blast.analyze`, `code.execute`, `spec.validate`, `test.generate` return constants; `code.execute` executes nothing and always reports `"28 passed"` (`plat/tools/computation.py:15-49`).
  - Action (5): `repo.write`, `repo.merge`, `notify.send`, `deploy.release`, `deploy.rollback` return dicts and change nothing (`plat/tools/action.py:24-42`).
  - Memory (3): `graph.write`, `graph.query`, `focal.extract` operate for real on the in-memory graph and ontology (`plat/tools/memory.py:32-101`).
- [CODE] `system.py`: one function builds key, approval service, audit store, graph, ontology, registry, policy, budget and gateway and returns a dataclass (`plat/system.py:69-101`). Clean and small; everything is in one address space by design ("in-memory and in-process", `docs/rfc/15-reference-implementation-status.md:17-19`).
- [CODE] `app.py`: `GET /health`, `GET /tools`, `POST /missions/run`, `GET /audit/verify`; no authentication dependency on any route; each run builds a fresh platform and uses the scripted approver (`plat/app.py:27-71`). Compose binds it to `0.0.0.0:8000` (`docker-compose.yml:15-17`).
- [CODE] `demo.py`: runs the mission and prints a report (`plat/demo.py:25-69`). Verified: exits 0, 28 audit events, `chain_valid=True`.
- [CODE] Cross-cutting absences, each confirmed by search and reading: persistence (none; all stores are dicts/lists); process isolation (single interpreter); authn/authz (none on any of the three FastAPI apps: `plat/app.py`, `approval/app.py:37-60`, `audit/app.py:35-76`); secrets (the stub string at `gateway/gateway.py:82`); egress control and sandboxing ([DOC-ONLY] `docs/rfc/07-security-governance.md:12`, `:88`; `docs/rfc/06-infrastructure.md:86`); kill switch / pause / emergency stop (no occurrence of such a concept in any Python file); redaction of secrets in logs or prompts (none).
- [DOC-ONLY] The status appendix is candid about this: "This is not production infrastructure ... the MCP 'tools' are deterministic stand-ins" (`docs/rfc/15-reference-implementation-status.md:21-26`) and lists real ingestion, vector search, HITL and observability surfaces as "not built" (`:96-97`).

### Inferences
- The reusable design assets are: the composition-root pattern, the `(principal, tool, args, context) → decision` shape, the gate helper that turns a pending action into an approval request plus an audit event (`plat/mission/orchestrator.py:76-129`), and the four-question forensic report idea. The six role agents, the 13-stage workflow, the corpus and the mission types are specific to the dropped use case.
- Moving from this to an always-on agent with real power is mostly new construction: an agent loop with a model, a scheduler/event intake, real tool adapters, a process and privilege architecture, and a human channel. The existing code gives semantics and tests to port, not a runtime.

### Gaps
- Contract-net bidding, A2A/ACP protocols and Temporal are documented but absent (`docs/rfc/15-reference-implementation-status.md:41`); nothing to evaluate.
- No evidence of how the design behaves with a non-deterministic model in the loop (tool-call loops, malformed args, retries).

## Repo hygiene relevant to a security tool: CI, Dockerfile, compose, dependencies

### Takeaway
Hygiene is at demo level. CI avoids the worst pattern (no `pull_request_target`) but pins actions by mutable tag, sets no `permissions`, and installs unpinned dependencies. The image runs as root from a tag-pinned base, and compose publishes an unauthenticated API on all interfaces. Dependencies are lower-bound ranges with no lock file or hashes; the suite happens to pass on today's much newer releases. There is no SAST, dependency audit, secret scanning, Dependabot, SECURITY.md or CODEOWNERS.

### Cited Findings
- [CODE] `.github/workflows/ci.yml`: triggers `push` and `pull_request` on `main` (`:7-11`); no `pull_request_target`. Actions referenced by tag: `actions/checkout@v4` (`:18`), `actions/setup-python@v5` (`:21`); not SHA-pinned. No `permissions:` key at workflow or job level, so the `GITHUB_TOKEN` gets the repository default. No `persist-credentials: false`, no `timeout-minutes`, no concurrency group. Steps: `pip install -r requirements.txt` (`:26`), `pytest` (`:29`), run demo (`:32`). No linter, type checker, bandit/semgrep, pip-audit, CodeQL or secret scan.
- [CODE] `.github/` contains only that workflow; there is no `dependabot.yml`, `SECURITY.md`, `CODEOWNERS` or pre-commit config in the repo.
- [CODE] `Dockerfile`: `FROM python:3.12-slim` by tag, no digest (`:6`); no `USER` instruction, so the process runs as root; `pip install --no-cache-dir -r requirements.txt` unpinned (`:12`); `COPY . .` ships tests and docs (`:15`); pytest is in the runtime image because there is one requirements file (`requirements.txt:8`).
- [CODE] `docker-compose.yml`: uvicorn on `0.0.0.0:8000`, published as `8000:8000` (`:15-17`); no `read_only`, `cap_drop`, `security_opt: no-new-privileges`, `user`, resource limits or network restrictions; healthcheck present (`:18-24`).
- [CODE] `requirements.txt`: eight packages, all `>=` lower bounds (`:1-8`); no lock file, no `--require-hashes`. `pyproject.toml` reads dependencies dynamically from it (`:20-23`), declares `requires-python >=3.10` (`:19`) while CI uses 3.12, and carries a stale comment "214 passed" (`:10`).
- [PROBE] A fresh install on 2026-11-10 resolved to fastapi 0.162.3, starlette 1.10.0, pydantic 2.14.3, cryptography 50.0.2, PyJWT 2.15.1, PyYAML 6.0.3, httpx 0.28.1, uvicorn 0.54.0, pytest 9.2.0 on Python 3.13.18. All 219 tests passed, with one deprecation warning (Starlette's test client deprecating `httpx`). So the build is not reproducible, and it currently works by luck of compatibility.
- [CODE] `.gitignore` has four entries (`.claude/`, `*.local.md`, `.venv/`, `__pycache__/`); it does not ignore `.pytest_cache`, `.env`, `*.pem` or key material.
- [CODE] Positive points: `yaml.safe_load` is used (`onto/loader.py:100`); checkpoint restore uses a model whitelist, not pickle (`mem/store.py:22-49`); JWT algorithm is pinned (`approval/service.py:140`); `.dockerignore` excludes `.git` and `.venv` (`.dockerignore:2-7`).
- [CODE] Documentation drift: the root `README.md` still describes R2P-IP and says "ADR-001…010" (`README.md:1-10`, `:31`) while ADR-011 exists; MIT `LICENSE` present.
- [CODE] Commit metadata in the public history uses what appears to be an employer-domain author identity (visible via `git log`); worth a deliberate decision for a public security tool.

### Inferences
- For a tool that will hold root-equivalent power and be "the biggest target on the box", the supply chain of the agent itself is in scope: SHA-pin actions, set `permissions: contents: read`, lock and hash dependencies (uv/pip-tools), pin the base image by digest, run as a non-root user with a read-only root filesystem and dropped capabilities, bind to loopback or a Unix socket, and add pip-audit plus a SAST pass to CI.
- The repo would also need to become its own first customer: the CI/CD hardening the agent is supposed to do for other repos is not yet applied here.

### Gaps
- GitHub-side settings (branch protection, required reviews, default workflow token permissions, secret scanning, Actions allow-list) are not visible from the checkout and were not verified.
- No SBOM or provenance attestation exists to review.

## Test suite: size, coverage, pass status, and what is not tested

### Takeaway
219 tests in 25 files, all passing in about 1.5 seconds. They pin the happy-path semantics of each kernel and a handful of negative cases (tamper, replay, wrong key, expiry, wrong role, tainted action, hidden trusted tier). They are specification tests for cooperative callers. None of the adversarial properties demonstrated by the probes in these notes is tested, and several cannot be, because the design does not provide them.

### Cited Findings
- [PROBE] `pytest` from repo root (config in `pytest.ini:1-25`): `219 passed, 1 warning in 1.52s` on Python 3.13.18 with the dependency versions listed above. The demo script exits 0.
- [PROBE] Per-package counts (collected): approval 26 (`test_api` 5, `test_keys` 3, `test_service` 18); audit 19 (`test_api` 4, `test_chain` 9, `test_store` 6); gateway 27 (`approval` 5, `budget_audit` 4, `policy` 13, `schema` 5); focal 30 (`extract` 18, `ppr` 7, `purposes` 5); ontology 37 (`export` 9, `loader` 11, `validate` 17); memory 36 (`assembler` 14, `claims` 7, `consolidation` 6, `store` 9); platform 44 (`agents` 8, `app` 4, `demo` 1, `mission` 16, `tools` 15). These match the status appendix's approximate figures (`docs/rfc/15-reference-implementation-status.md:30-41`).
- [CODE] What is covered:
  - Audit: genesis and linkage, tampered middle event, relink detected at next event, non-monotonic seq, Merkle determinism, concurrent appends (`backend/audit/tests/test_chain.py:53`, `:65`; `test_store.py`).
  - Approval: claims present, replay rejected, params mismatch (and that it does not consume), flipped byte, wrong key, expiry, typed consequence, dual control with same/different approver strings (`backend/approval/tests/test_service.py`).
  - Gateway: family allow rules, unknown tool, taint blocks action even with a valid token, top-level and nested trusted-tier write, provenance key required, role scope for deploy, budget exhaustion, handler error audited, schema required/type/enum (`backend/gateway/tests/`).
  - Platform: golden mission completes, each gate rejection aborts, failed merge aborts, token single-use and bound to args, perception results tagged, staging excluded and opt-in taints brief (`platform/tests/`).
- [CODE] Test fixtures use a different `graph.write` argument shape (`mutations`, with an echo handler) from the platform's real handler (`nodes`/`edges`) (`backend/gateway/tests/gateway_helpers.py:114-129` vs `plat/tools/memory.py:104-118`), so gateway-level tests of memory rules do not exercise the real write path.
- [PROBE] Properties with no test, each shown false or absent by a probe in the sections above:
  - Taint: untrusted result followed by action without self-declaration; trusted write from a self-declared trusted turn; tainted overwrite of a trusted node; tainted edge insertion; gateway `result_taint` for a staging-inclusive focal brief; fence-delimiter escape.
  - Approval: cross-tool token reuse; token burned by budget denial or handler error; replay after restart; unauthenticated approver; dual control by two invented strings; pending-request expiry; evidence/hash mismatch.
  - Audit: tail truncation; full recomputation; forged events via the REST app; segment verification; outcome and reason recording; unhashable args producing no event.
  - Gateway: direct handler invocation; forged principal role; tool re-registration; extra/nested/hostile arguments; approval-flagged tools in the computation family; any-agent `repo.merge`.
  - Memory: claim text unrelated to cited evidence; lesson overwrite by similarity; restore of a tampered checkpoint.
- [CODE] No fuzzing, property-based tests, concurrency tests beyond audit append, or coverage measurement; CI runs only `pytest` and the demo (`.github/workflows/ci.yml:28-32`).

### Inferences
- The suite is valuable as a set of golden semantics to port (ADR-011 calls the suites "the contract", `docs/adr/011-python-reference-implementations.md:16-20`), and it is fast enough to be a pre-commit gate. It should not be read as security assurance: its one adversarial finding to date (the nested-tier bypass) came from a manual review, not from the tests.
- Each probe above converts directly into a regression test; several will fail until the architecture changes (process separation, gateway-owned taint, external audit anchor), which makes them a useful definition of done for the security-agent refactor.

### Gaps
- No red-team corpus of injection payloads, no model-in-the-loop evaluation, and no tests of real tools exist, because none of those components exist.
- Coverage percentages were not measured (no coverage tooling configured; adding it was out of scope for a read-only review).

## Overall: KEEP / CHANGE / DROP per component for the security-agent use case, and what is missing entirely

### Takeaway
Keep the ideas and the small kernels; change who supplies their inputs and where they run; drop the research-to-product shell. The largest gap is not in any one component but in the trust architecture: today the agent, the policy engine, the approval signer, the audit log and the tools share one process and one set of in-memory objects, so every guarantee reduces to "the agent's code chose to behave". A security agent that is the main target on its own box needs those to be separate principals with the agent holding the least privilege of all.

### Cited Findings

Verdicts (each justified from the evidence in the sections above)

- **Gateway choke point (`gateway/gateway.py`) — KEEP the design, CHANGE the implementation substantially.** The pipeline shape and the one-event-per-call discipline are right and tested (`gateway/gateway.py:47-107`). It must become a separate, authenticated process that alone holds credentials; write an intent record before execution and an outcome record after (`gateway/gateway.py:87`, `:102`); record reason, policy version and result hash (`gateway/gateway.py:111-122`); pass context to handlers; and survive unhashable input (`gateway/policy.py:27-30`). Without process separation the bypass shown by direct handler call makes the rest moot.

- **Policy engine (`gateway/policy.py`) — CHANGE.** Keep ordered evaluation and default-deny (`gateway/policy.py:95-101`). Replace first-match-wins with deny-overrides, add a target-scope rule and a `ToolDef` target declaration, make role-to-tool mapping data rather than two hard-coded prefixes (`gateway/policy.py:24`, `:150-165`), remove the blanket allow for perception/computation (`gateway/policy.py:122-132`), and move rules into a reviewed, hash-pinned policy file whose version is logged. Roughly a rewrite of 200 lines, guided by the existing tests.

- **Schema validation (`gateway/validation.py`) — DROP and replace.** Forty lines covering required/type/enum at top level only (`gateway/validation.py:21-41`). Use a real JSON Schema validator with `additionalProperties: false`, nested validation and string constraints, plus semantic validators for hosts, paths and URLs.

- **Budget governor (`gateway/budget.py`) — CHANGE.** Keep the atomic check-and-consume (`gateway/budget.py:25-32`). Add time windows, per-tool and per-target limits, metered-by-default, persistence, and move the check before token consumption.

- **Tool registry (`gateway/registry.py`) — CHANGE.** Keep the typed `ToolDef`. Forbid silent overwrite (`gateway/registry.py:34-35`), load from a signed manifest, pin tool/MCP server versions and hashes, add target-parameter metadata and reversibility/undo metadata, and replace the four research-era families with classes that separate passive read, active probe, reversible change and irreversible change.

- **Taint firewall (ADR-008; `gateway/policy.py:105-120`, `plat/agents/runtime.py:107-143`) — KEEP the principle (mechanical damage cap, evaluated before approval), CHANGE the mechanism completely.** Taint must be latched by the gateway from perception results, persisted per session, attached to stored values, and consulted through a taint × tool × scope × reversibility matrix with typed declassification. The present caller-declared binary flag does not constrain a compromised or merely careless agent, and if enforced honestly would block alerting and containment.

- **Approval tokens (`approval/`) — KEEP the crypto core, CHANGE binding, state and placement.** EdDSA with pinned algorithm, TTL and `jti` are sound (`approval/service.py:120-162`). Add tool, principal, target, session and scope-hash claims and verify them all; include the tool name in the hash; make consumption two-phase and durable; expire pending requests; have the service render what it signs; authenticate the approver out of band; move the private key off the agent's process and preferably off the VM (`plat/system.py:79-80`).

- **Audit chain (`audit/`) — KEEP the chain and verifier, CHANGE storage, authenticity and content.** The hashing is correct (`audit/chain.py:16-69`). Add durable append-only storage under a different OS user, per-event or per-checkpoint signatures, continuous off-box anchoring of the head, checkpoint-relative verification, and a richer event schema. Remove or authenticate the append endpoint (`audit/app.py:40-42`).

- **Risk score and autonomy mode (`plat/agents/roles.py:23-49`) — DROP the formula, CHANGE the concept.** The inputs are software-change metrics from a stub and the mode has no effect. Re-derive risk in the gateway from owner-maintained asset criticality, signed tool metadata, scope and taint, and make the mode select real behaviour.

- **Ontology loader/validator (`onto/`) — KEEP.** Small, tested, domain-neutral (`onto/loader.py`, `onto/validate.py`). Extend with cardinality and value-type rules and move the provenance source enum into YAML (`onto/models.py:11`).

- **Ontology content (`ontology-v1.yaml`) — DROP and rewrite** as a security ontology; about ten of the 24 node types and two of the 13 relations carry over.

- **Graph store (`focal/graph.py`) — DROP as a store, replace.** No provenance, silent overwrite, no history or persistence (`focal/graph.py:15-27`, `:73`). SQLite with append-only versioned rows would already be an improvement for a single VM.

- **Focal extraction (`focal/extract.py`, `ppr.py`, `purposes.py`) — KEEP the algorithm, CHANGE the profiles, low priority.** Deterministic, explainable retrieval with a coverage note is a good fit for triage briefs; purposes and edge weights are research-specific (`focal/purposes.py:23-100`); rendering must fence by provenance, not by a caller flag (`focal/extract.py:376-378`).

- **Prompt assembler (`mem/assembler.py`) — KEEP, small CHANGE.** Deterministic, budgeted, hashed assembly is directly useful. Fix delimiter escaping with a per-prompt random fence and store prompt text (or an encrypted copy) so hashes in the audit log are resolvable.

- **Grounded-claim check (`mem/claims.py`) — KEEP the hook, CHANGE the substance.** Move ledger ownership to the gateway, add result hashes and an evidence store, and add finding-class → evidence-type rules. Today it enforces citation, not support (`mem/claims.py:12-34`).

- **LessonStore and SessionMemoryStore (`mem/consolidation.py`, `mem/store.py`) — HOLD (do not wire as-is).** The similarity overwrite with no provenance (`mem/consolidation.py:51-64`) is a poisoning primitive for a long-lived agent; add authorship, taint, history and human review before any model reads lessons. The session store is harmless but needs integrity on restore.

- **Orchestrator, role agents, corpus, mission types, demo, scripted approvers (`plat/mission/`, `plat/agents/roles.py`, `plat/corpus.py`, `plat/demo.py`, `plat/types.py`) — DROP**, keeping the gate-helper pattern (`plat/mission/orchestrator.py:76-129`) and the forensic-report idea. They encode the abandoned workflow and contain no model integration.

- **Tool handlers (`plat/tools/*.py`) — DROP all**; they are constants. Keep nothing but the registration pattern.

- **Composition root (`plat/system.py`) — KEEP the pattern, CHANGE the topology** from one in-process object graph to wiring of separate services.

- **FastAPI apps (`plat/app.py`, `approval/app.py`, `audit/app.py`) — DROP or rebuild** with authentication, loopback/Unix-socket binding, and a working verify endpoint (`plat/app.py:65-69` verifies an empty chain).

- **CI, Dockerfile, compose, dependency files — CHANGE** as listed in the hygiene section.

- **RFC/ADR set (`docs/`) — KEEP ADR-004, 008, 009 as statements of intent, rewrite the rest.** Several claims in them are not true of the code (per-turn taint inspection, token hash in audit, KMS keys, WORM anchoring, Steiner pruning); the status appendix (`docs/rfc/15-reference-implementation-status.md`) is the honest document and should be the model.

Missing entirely (no code, in some cases no design)
- An agent: model integration, tool-calling loop, retry/timeout handling, context management with a real model.
- An always-on runtime: daemon/service unit, scheduler, event intake, queueing, crash recovery, state persistence of any kind.
- Sensors and data sources: journald/auditd/eBPF/osquery/Falco/Suricata/file-integrity/package and container inventory, CI/CD and repository event feeds, vulnerability feeds.
- Real effectors: firewall, process, service, package, credential, repository and pipeline adapters, each with a tested undo.
- Scope and rules-of-engagement enforcement: owner-signed asset inventory and allowlist (hosts, CIDRs, repos, accounts, paths, time windows), enforced in the gateway and again at OS/network level.
- Privilege separation: distinct OS users/processes for model-facing agent, gateway, approval signer and audit writer; per-tool least privilege (sudoers rules, capabilities, namespaces); the agent process itself unprivileged.
- Kill switch and safe mode: an out-of-band stop that the agent cannot disable, automatic degradation to read-only on anomaly, dead-man timer.
- Egress control: default-deny outbound with an allowlisting proxy for model API, package registries and update sources; DNS control. Mentioned in docs only (`docs/adr/008-taint-tool-firewall.md:16`).
- Sandboxing for analysis of untrusted artifacts and for any code execution (`plat/tools/computation.py:34-37` is a constant).
- Secrets management and redaction: credential storage outside the agent, short-lived scoped credentials, scrubbing of secrets from prompts, logs, evidence and anything sent to a model provider.
- Tool and MCP supply-chain controls: signed tool manifests, version/hash pinning, tool-description integrity (tool-poisoning and rug-pull defence), per-server network and filesystem confinement.
- Evidence store: immutable, content-addressed capture of tool outputs with chain of custody, linked from findings and from audit events.
- Authenticated human channel: real approval UI or chat-ops with strong approver authentication, readable diffs of what is being approved, notification delivery, approval-fatigue controls.
- Durable, externally anchored audit (described above) and trusted time.
- Self-protection: integrity monitoring of the agent's own binaries, config, policy and memory; detection of attempts to alter scope, policy or logs; update and rollback procedure for the agent.
- Information-flow control across turns and memory (labels on values, declassification rules), and a prompt-injection test corpus with model-in-the-loop evaluation.
- Operational basics: configuration management, metrics, health and liveness, rate limiting by time, backup and restore, incident runbooks, data retention.

### Inferences
- Order of work that follows from the evidence, for a solo engineer: (1) process and privilege separation with the gateway as the sole credential holder; (2) scope allowlist plus deny-overrides policy; (3) durable signed audit with off-box head; (4) approval token rebinding and an out-of-band approver; (5) gateway-owned taint with a policy matrix and typed declassification; (6) only then real sensors, effectors and a model. Steps 1–4 are needed before the agent is given any real power; the existing kernels and tests shorten 3 and 4 noticeably and help little with 1, 2 and 6.
- Rough proportion: of ~4,000 lines, perhaps 600–800 (audit chain, token service core, ontology loader/validator, prompt assembler, PPR/extract) carry over with modification; the rest is either demo scaffolding to delete or thin code to rewrite. The transferable value is mainly the threat-model thinking in ADR-004/008/009 and a test style that pins semantics.
- The repo's own history supports caution about self-assessment: the one acknowledged security bug (commit `3d47b97`) was found by adversarial review after the tests were green, and this review found over twenty further gaps of the same kind in a single pass using short probe scripts.

### Gaps
- No performance, reliability or cost data exists for any component under realistic load, and none could be produced without real tools and a model.
- This review did not assess the unimplemented Go/OPA/Vault/Temporal target architecture described in the RFCs, only the code present; whether that target would suit a single self-hosted VM is a separate design question (it is specified for multi-tenant Kubernetes, `docs/rfc/15-reference-implementation-status.md:21`).
- Legal and rules-of-engagement aspects of red-team tooling against the owner's systems are outside the code and were not examined.
