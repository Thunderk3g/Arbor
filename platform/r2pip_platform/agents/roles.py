"""The supervised-swarm role agents (RFC-001 §2.2), as deterministic policies.

These are not LLM calls — they are scripted behaviors that exercise the real
platform machinery in the shape the golden mission describes. Each method drives
its runtime through think() (audited prompt) → call() (gateway tool calls) and
returns a structured result the orchestrator gates and records.

The Developer's two-turn build is the security set-piece: turn 1 ingests an
untrusted paper and an attempted ``repo.write`` is firewalled; turn 2 is a fresh
clean-context turn that commits the sandbox-validated artifact (walkthrough §8-9).
"""

from __future__ import annotations

from r2pip_memory import Claim, summary_for_claims_sheet

from r2pip_platform.types import MissionSpec, Role


# --- risk scoring (RFC-001 §1.7, §5 stage 6) -------------------------------

# Autonomy-mode thresholds on the composite risk score R.
_AUTONOMOUS_BELOW = 0.30
_MANUAL_AT_OR_ABOVE = 0.65


def compute_risk_score(blast_radius: dict, *, novelty: float = 0.0) -> tuple[float, str]:
    """R = f(blast_radius, reversibility, untested_fraction, novelty) -> (R, mode).

    Reversibility is folded in by the orchestrator (a rollback path exists, so
    no extra penalty here). Mode selects the HITL posture for the merge gate.
    """
    symbols = blast_radius.get("symbols", 0)
    services = blast_radius.get("services", 0)
    untested = blast_radius.get("untested_fraction", 0.0)
    r = (
        0.45 * min(symbols / 40.0, 1.0)
        + 0.35 * min(services / 4.0, 1.0)
        + 0.20 * float(untested)
        + float(novelty)
    )
    r = round(min(r, 1.0), 2)
    if r < _AUTONOMOUS_BELOW:
        mode = "autonomous"
    elif r < _MANUAL_AT_OR_ABOVE:
        mode = "supervised"
    else:
        mode = "manual"
    return r, mode


class _BaseRole:
    role: Role

    def __init__(self, platform, runtime) -> None:
        self.platform = platform
        self.runtime = runtime


class BIAgent(_BaseRole):
    role = Role.BI

    def mine_opportunity(self, mission_id: str, spec: MissionSpec) -> dict:
        """Stage 0: focal opportunity-mining sweep → write an Opportunity node."""
        rt = self.runtime
        task_id, trace_id = "T0-insight", f"{mission_id}-t0"

        focal = rt.call(
            "focal.extract",
            {"seed_ids": spec.opportunity_seed_ids, "purpose": "opportunity_mining"},
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
        )
        fg = focal.result
        rt.think(
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
            system="You are the BI agent. Find research-to-product arbitrage.",
            focal_context=fg["rendered_context"], focal_taint=fg["taint"],
        )

        opp_id = "opp-cyclelife"
        write = rt.call(
            "graph.write",
            {
                "provenance": {
                    "source_type": "agent_inference", "source_ref": fg["focal_graph_id"],
                    "extractor": "bi-agent@1.0", "confidence": 0.81, "taint": "trusted",
                },
                "tier": "trusted",
                "nodes": [{
                    "id": opp_id, "type": "Opportunity",
                    "canonical_name": "Cycle-life pricing for grid-storage contracts",
                    "metadata": {"thesis": (
                        "LHCE degradation model addresses cycle-life modeling demand "
                        "signaled by the grid-storage RFP wave."
                    )},
                    "confidence": 0.81, "tier": "trusted",
                }],
            },
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
        )
        return {
            "opportunity_id": opp_id,
            "focal_path": fg["coverage_note"],
            "nodes_in_brief": [n["id"] for n in fg["nodes"]],
            "write_status": write.status,
            "audit_seqs": [focal.audit_seq, write.audit_seq],
        }


class POAgent(_BaseRole):
    role = Role.PO

    def draft_spec(self, mission_id: str, spec: MissionSpec, opportunity_id: str) -> dict:
        """Stage 1: PR/FAQ + ARS; spec.validate; write the ARS node."""
        rt = self.runtime
        task_id, trace_id = "T1-spec", f"{mission_id}-t1"

        focal = rt.call(
            "focal.extract",
            {"seed_ids": [opportunity_id, "need-cyclelife", "method-lhce"], "purpose": "spec_drafting"},
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
        )
        rt.think(
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
            system="You are the PO agent. Draft a PR/FAQ and an ARS.",
            focal_context=focal.result["rendered_context"], focal_taint=focal.result["taint"],
        )

        ars = {
            "version": "ARS-142",
            "title": spec.title,
            "functional_requirements": [
                "Expose cycle-life prediction in the pricing API response.",
            ],
            "acceptance_criteria": [
                "AC1: /price returns cycle_life_estimate for valid contracts.",
                "AC2: estimate within paper-reported tolerance.",
                "AC3: latency budget unchanged.",
            ],
            "non_goals": ["No schema changes to billing."],
        }
        validate = rt.call(
            "spec.validate", {"ars": ars},
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
        )

        ars_id = "ars-142"
        write = rt.call(
            "graph.write",
            {
                "provenance": {
                    "source_type": "agent_inference", "source_ref": opportunity_id,
                    "extractor": "po-agent@1.0", "confidence": 0.9, "taint": "trusted",
                },
                "tier": "trusted",
                "nodes": [{
                    "id": ars_id, "type": "ARS", "canonical_name": "ARS-142",
                    "metadata": {"version": "ARS-142", "statement": spec.title},
                    "confidence": 0.9, "tier": "trusted",
                }],
            },
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
        )
        return {
            "ars_id": ars_id, "ars": ars,
            "spec_valid": validate.result["valid"],
            "audit_seqs": [focal.audit_seq, validate.audit_seq, write.audit_seq],
        }


class HeadEngineer(_BaseRole):
    role = Role.HEAD_ENGINEER

    def plan(self, mission_id: str, spec: MissionSpec) -> dict:
        """Stage 2: ast/deps/blast analysis → risk score + autonomy mode + DAG."""
        rt = self.runtime
        task_id, trace_id = "T2-plan", f"{mission_id}-t2"
        repo = spec.target_service

        rt.think(
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
            system="You are the Head Engineer. Decompose and assess blast radius.",
        )
        ast = rt.call("ast.analyze", {"repo": repo}, mission_id=mission_id, task_id=task_id, trace_id=trace_id)
        deps = rt.call("deps.graph", {"repo": repo}, mission_id=mission_id, task_id=task_id, trace_id=trace_id)
        blast = rt.call("blast.analyze", {"repo": repo}, mission_id=mission_id, task_id=task_id, trace_id=trace_id)

        blast_radius = blast.result["blast_radius"]
        risk, mode = compute_risk_score(blast_radius, novelty=0.10)
        dag = [
            {"task": "T1", "desc": "Port LHCE model (license-checked)"},
            {"task": "T2", "desc": "Add /price cycle-life field"},
            {"task": "T3", "desc": "Backtest harness"},
        ]
        return {
            "risk_score": risk, "autonomy_mode": mode,
            "blast_radius": blast_radius,
            "rollback_strategy": "revert merge; no migrations",
            "task_dag": dag,
            "symbols": ast.result["symbols"],
            "audit_seqs": [ast.audit_seq, deps.audit_seq, blast.audit_seq],
        }


class DeveloperAgent(_BaseRole):
    role = Role.DEVELOPER

    def build(self, mission_id: str, spec: MissionSpec) -> dict:
        """Stages 8-9: tainted study turn (firewalled write) + clean commit turn."""
        rt = self.runtime
        task_id, trace_id = "T-dev", f"{mission_id}-dev"
        repo = spec.target_service

        # --- turn 1: study the paper (UNTRUSTED) -------------------------------
        rt.call("research.search", {"query": "lhce cycle-life model"},
                mission_id=mission_id, task_id=task_id, trace_id=trace_id)
        fetch = rt.call("research.fetch", {"ref": "arxiv:2401.00001"},
                        mission_id=mission_id, task_id=task_id, trace_id=trace_id)
        paper_text = fetch.result["content"]

        # The prompt now holds untrusted paper text -> this turn is tainted.
        rt.think(
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
            system="You are Dev-7. Implement T1/T2 from the brief.",
            untrusted_data=paper_text,
        )
        # Attempting to commit in the tainted turn must be firewalled (ADR-008).
        blocked = rt.call(
            "repo.write",
            {"repo": repo, "branch": "agent/dev-7/cycle-life", "diff": "from-untrusted-turn"},
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
            taint="external_untrusted",
        )
        # Work proceeds in the sandbox via Computation tools (allowed under taint).
        sandbox = rt.call(
            "code.execute",
            {"code": "def price_with_cycle_life(...): ...", "network": "package_registries"},
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
            taint="external_untrusted",
        )
        sandbox_ledger = rt.last_ledger_id(task_id)

        # --- turn 2: fresh clean context, commit validated artifact ------------
        rt.fresh_context(task_id)
        rt.think(
            mission_id=mission_id, task_id=task_id, trace_id=f"{trace_id}-clean",
            system="You are Dev-7. Commit the sandbox-validated artifact.",
        )
        commit = rt.call(
            "repo.write",
            {"repo": repo, "branch": "agent/dev-7/cycle-life", "diff": "validated-artifact"},
            mission_id=mission_id, task_id=task_id, trace_id=f"{trace_id}-clean",
            taint="trusted",
        )
        commit_ledger = rt.last_ledger_id(task_id)

        # --- claims sheet (B.4: every claim cites an ok tool-ledger entry) -----
        tm = rt.task_memory(task_id)
        tm.claims.append(Claim(
            text="Implemented cycle-life prediction in sandbox; 28 cases pass.",
            evidence_ledger_id=sandbox_ledger,
        ))
        tm.claims.append(Claim(
            text="Committed validated artifact to agent branch.",
            evidence_ledger_id=commit_ledger,
        ))
        claims_sheet = summary_for_claims_sheet(tm)
        declared_scope = {"symbols_touched": 11, "touches_billing": False}

        return {
            "blocked_write_status": blocked.status,
            "blocked_write_reason": blocked.reason,
            "sandbox_passed": sandbox.result["passed"],
            "commit": commit.result["commit"],
            "branch": "agent/dev-7/cycle-life",
            "claims_sheet": claims_sheet,
            "declared_scope": declared_scope,
        }


class QAAgent(_BaseRole):
    role = Role.QA
    MUTATION_BASELINE = 0.70

    def validate(self, mission_id: str, spec: MissionSpec) -> dict:
        rt = self.runtime
        task_id, trace_id = "T-qa", f"{mission_id}-qa"
        rt.think(
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
            system="You are QA-1. Generate tests and validate the claims sheet.",
        )
        gen = rt.call(
            "test.generate", {"target": spec.target_service},
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
        )
        score = gen.result["mutation_score"]
        return {
            "mutation_score": score,
            "baseline": self.MUTATION_BASELINE,
            "passed": score >= self.MUTATION_BASELINE,
            "dissent": "AC3 tolerance ambiguous (resolved by Head Engineer)",
            "tests_added": gen.result["tests_added"],
        }


class InfraAgent(_BaseRole):
    role = Role.INFRA

    def deploy(self, mission_id: str, spec: MissionSpec, deploy_args: dict, token: str) -> dict:
        """Stage 12: deploy.release bound to the image digest via the H5 token."""
        rt = self.runtime
        task_id, trace_id = "T-deploy", f"{mission_id}-deploy"
        rt.think(
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
            system="You are the Infra agent. Execute the approved canary release.",
        )
        release = rt.call(
            "deploy.release", deploy_args,
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
            taint="trusted", approval_token=token,
        )
        record = rt.call(
            "graph.write",
            {
                "provenance": {
                    "source_type": "agent_inference", "source_ref": deploy_args["image_digest"],
                    "extractor": "infra-agent@1.0", "confidence": 1.0, "taint": "trusted",
                },
                "tier": "trusted",
                "nodes": [{
                    "id": f"deploy-{mission_id}", "type": "DeploymentRecord",
                    "canonical_name": f"release {spec.target_service}",
                    "metadata": {"service": spec.target_service, "revision": deploy_args["image_digest"]},
                    "confidence": 1.0, "tier": "trusted",
                }],
            },
            mission_id=mission_id, task_id=task_id, trace_id=trace_id,
        )
        return {
            "release_status": release.status,
            "release_reason": release.reason,
            "released": release.result["released"] if release.status == "ok" else False,
            "audit_seqs": [release.audit_seq, record.audit_seq],
        }
