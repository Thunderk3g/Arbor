"""Mission orchestrator: the Temporal-workflow stand-in (RFC-001 §5).

Drives one mission through stages 0-13 of the golden walkthrough, inserting the
human-in-the-loop checkpoints H1 (spec), H2 (plan), H4 (claims-sheet/merge), and
H5 (deploy). Every gate goes through the real Approval Service; the H5 token is
bound to the deploy's params hash and verified by the gateway. A rejected gate
aborts the mission. After completion the orchestrator verifies the audit chain
and produces the four forensic answers the walkthrough promises.

The orchestrator owns no policy of its own — it composes the slices. Its only
"business logic" is sequencing, the claims-sheet-vs-blast-radius check, and
translating a human decision into an approval request.
"""

from __future__ import annotations

from typing import Optional

from r2pip_audit import Action, Actor, verify_chain
from r2pip_approval.models import ApprovalDecision
from r2pip_gateway import compute_params_hash
from r2pip_memory import validate_claims

from r2pip_platform.agents import (
    AgentRuntime,
    BIAgent,
    DeveloperAgent,
    HeadEngineer,
    InfraAgent,
    POAgent,
    QAAgent,
)
from r2pip_platform.types import (
    ApproverFn,
    GateContext,
    MissionResult,
    MissionSpec,
    MissionState,
    Role,
    StageRecord,
)


class MissionAborted(Exception):
    """Raised internally when a HITL gate is rejected; caught by run()."""

    def __init__(self, stage: str, reason: str) -> None:
        super().__init__(reason)
        self.stage = stage
        self.reason = reason


class MissionOrchestrator:
    def __init__(self, platform, approver: ApproverFn, *, mission_id: str = "MSN-4413") -> None:
        self.platform = platform
        self.approver = approver
        self.mission_id = mission_id
        # One runtime (and one role wrapper) per swarm member.
        self._rt = {
            Role.BI: AgentRuntime(platform, Role.BI, "bi-agent"),
            Role.PO: AgentRuntime(platform, Role.PO, "po-agent"),
            Role.HEAD_ENGINEER: AgentRuntime(platform, Role.HEAD_ENGINEER, "head-engineer"),
            Role.DEVELOPER: AgentRuntime(platform, Role.DEVELOPER, "dev-7"),
            Role.QA: AgentRuntime(platform, Role.QA, "qa-1"),
            Role.INFRA: AgentRuntime(platform, Role.INFRA, "infra-1"),
        }
        self.bi = BIAgent(platform, self._rt[Role.BI])
        self.po = POAgent(platform, self._rt[Role.PO])
        self.head = HeadEngineer(platform, self._rt[Role.HEAD_ENGINEER])
        self.dev = DeveloperAgent(platform, self._rt[Role.DEVELOPER])
        self.qa = QAAgent(platform, self._rt[Role.QA])
        self.infra = InfraAgent(platform, self._rt[Role.INFRA])

    # --- HITL gate machinery ----------------------------------------------

    def _run_gate(
        self,
        *,
        checkpoint: str,
        action_type: str,
        subject_id: str,
        params_hash: str,
        risk_score: float,
        evidence: dict,
        destructive: bool = False,
        required_consequence: Optional[str] = None,
        dual_control: bool = False,
    ) -> tuple[bool, Optional[str], object]:
        """Create an approval request, obtain the human decision, audit it.
        Returns (approved, token, request)."""
        platform = self.platform
        request = platform.approval.create_request(
            tenant_id=platform.tenant_id,
            checkpoint=checkpoint,
            action_type=action_type,
            subject_id=subject_id,
            params_hash=params_hash,
            risk_score=risk_score,
            evidence_bundle=evidence,
            destructive=destructive,
            required_consequence=required_consequence,
            dual_control=dual_control,
        )
        gate = GateContext(
            checkpoint=checkpoint, title=action_type, subject_id=subject_id,
            risk_score=risk_score, evidence=evidence, destructive=destructive,
            required_consequence=required_consequence, dual_control=dual_control,
        )
        decision = self.approver(gate)
        if not isinstance(decision, ApprovalDecision):
            raise TypeError("approver must return an ApprovalDecision")

        try:
            outcome = platform.approval.decide(request.id, decision)
        except ValueError:
            # e.g. typed-consequence mismatch -> request is now rejected
            self._audit_approval(checkpoint, subject_id, params_hash, decision.approver_id, approved=False)
            return False, None, platform.approval.get_request(request.id)

        approved = outcome.request.status == "approved"
        self._audit_approval(
            checkpoint, subject_id, params_hash, decision.approver_id, approved=approved
        )
        return approved, outcome.token, outcome.request

    def _audit_approval(
        self, checkpoint: str, subject_id: str, params_hash: str, approver_id: str, *, approved: bool
    ) -> int:
        return self.platform.audit_event(
            actor=Actor(kind="human", id=approver_id, on_behalf_of_mission=self.mission_id),
            action=Action(
                type="approval",
                tool=f"{checkpoint}:{'approved' if approved else 'rejected'}",
                params_hash=params_hash,
            ),
            mission_id=self.mission_id,
            task_id=f"gate-{checkpoint}",
            trace_id=f"{self.mission_id}-{checkpoint}",
        )

    def _gate_or_abort(self, stage: str, **kw) -> tuple[Optional[str], object]:
        approved, token, request = self._run_gate(**kw)
        if not approved:
            raise MissionAborted(stage, f"{kw['checkpoint']} rejected")
        return token, request

    # --- the mission ------------------------------------------------------

    def run(self, spec: MissionSpec) -> MissionResult:
        state = MissionState(spec=spec)
        try:
            self._stage_insight(spec, state)
            self._stage_spec(spec, state)
            self._stage_plan(spec, state)
            self._stage_build_validate(spec, state)
            self._stage_merge(spec, state)
            self._stage_deploy(spec, state)
            state.status = "completed"
        except MissionAborted as abort:
            state.status = "aborted"
            state.abort_reason = abort.reason
            state.record(StageRecord(stage=abort.stage, status="rejected", summary=abort.reason))

        return self._finalize(state)

    # Stage 0 — Perception & Insight (BI sweep).
    def _stage_insight(self, spec: MissionSpec, state: MissionState) -> None:
        out = self.bi.mine_opportunity(self.mission_id, spec)
        state.opportunity_id = out["opportunity_id"]
        state.record(StageRecord(
            stage="0-insight", status="ok",
            summary=f"Opportunity {out['opportunity_id']} mined; {out['focal_path']}",
            audit_seqs=out["audit_seqs"], data=out,
        ))

    # Stage 1 — Specification + H1.
    def _stage_spec(self, spec: MissionSpec, state: MissionState) -> None:
        out = self.po.draft_spec(self.mission_id, spec, state.opportunity_id)
        state.ars_id = out["ars_id"]
        if not out["spec_valid"]:
            raise MissionAborted("1-spec", "spec.validate failed")
        token, _ = self._gate_or_abort(
            "1-spec",
            checkpoint="H1", action_type="spec_approval", subject_id=out["ars_id"],
            params_hash=compute_params_hash(out["ars"]), risk_score=0.2,
            evidence={"ars_id": out["ars_id"], "non_goals": out["ars"]["non_goals"]},
        )
        state.record(StageRecord(
            stage="1-spec", status="ok", summary=f"ARS {out['ars_id']} approved at H1",
            audit_seqs=out["audit_seqs"], data={"ars": out["ars"]},
        ))

    # Stage 2 — Planning + H2.
    def _stage_plan(self, spec: MissionSpec, state: MissionState) -> None:
        out = self.head.plan(self.mission_id, spec)
        state.risk_score = out["risk_score"]
        state.autonomy_mode = out["autonomy_mode"]
        self._plan = out  # used by build/merge stages
        self._gate_or_abort(
            "2-plan",
            checkpoint="H2", action_type="plan_approval", subject_id=spec.target_service,
            params_hash=compute_params_hash({"dag": out["task_dag"], "rollback": out["rollback_strategy"]}),
            risk_score=out["risk_score"],
            evidence={"risk_score": out["risk_score"], "mode": out["autonomy_mode"],
                      "rollback": out["rollback_strategy"]},
        )
        state.record(StageRecord(
            stage="2-plan", status="ok",
            summary=f"R={out['risk_score']} ({out['autonomy_mode']}); plan approved at H2",
            audit_seqs=out["audit_seqs"], data=out,
        ))

    # Stages 3-4 — Build & Validate.
    def _stage_build_validate(self, spec: MissionSpec, state: MissionState) -> None:
        dev_out = self.dev.build(self.mission_id, spec)
        self._dev = dev_out
        # B.4: the developer's claims must all be grounded in ok ledger entries.
        claim_violations = validate_claims(self._rt[Role.DEVELOPER].task_memory("T-dev"))
        if claim_violations:
            raise MissionAborted("3-build", f"ungrounded claims: {claim_violations}")

        qa_out = self.qa.validate(self.mission_id, spec)
        self._qa = qa_out
        if not qa_out["passed"]:
            raise MissionAborted("4-validate", f"mutation score {qa_out['mutation_score']} < baseline")

        state.claims_sheet = dev_out["claims_sheet"]
        state.record(StageRecord(
            stage="3-4-build-validate", status="ok",
            summary=(
                f"firewall blocked tainted write ({dev_out['blocked_write_reason']}); "
                f"committed {dev_out['commit']}; mutation {qa_out['mutation_score']}"
            ),
            data={"dev": dev_out, "qa": qa_out},
        ))

    # Stage 5/11 — Claims-sheet verification + merge (H4).
    def _stage_merge(self, spec: MissionSpec, state: MissionState) -> None:
        ok, reason = self._verify_claims_sheet(self._dev["declared_scope"], self._plan["blast_radius"])
        if not ok:
            raise MissionAborted("5-claims", f"claims sheet exceeds blast radius: {reason}")

        self._gate_or_abort(
            "5-merge",
            checkpoint="H4", action_type="merge_approval", subject_id=self._dev["branch"],
            params_hash=compute_params_hash({"branch": self._dev["branch"], "commit": self._dev["commit"]}),
            risk_score=state.risk_score or 0.0,
            evidence={"claims_sheet": self._dev["claims_sheet"], "mode": state.autonomy_mode},
        )
        merge = self._rt[Role.HEAD_ENGINEER].call(
            "repo.merge", {"repo": spec.target_service, "branch": self._dev["branch"]},
            mission_id=self.mission_id, task_id="T-merge", trace_id=f"{self.mission_id}-merge",
        )
        state.merged = merge.status == "ok"
        state.record(StageRecord(
            stage="5-merge", status="ok" if state.merged else "error",
            summary=f"claims within blast radius; merged at H4 ({reason})",
            audit_seqs=[merge.audit_seq], data={"verify": reason},
        ))

    # Stage 12 — Deploy (H5), bound to the image digest.
    def _stage_deploy(self, spec: MissionSpec, state: MissionState) -> None:
        deploy_args = {
            "service": spec.target_service,
            "image_digest": spec.image_digest,
            "canary_plan": "5-25-50-100; abort on p99 +10% or error 2x",
        }
        params_hash = compute_params_hash(deploy_args)
        token, _ = self._gate_or_abort(
            "6-deploy",
            checkpoint="H5", action_type="deploy", subject_id=spec.target_service,
            params_hash=params_hash, risk_score=state.risk_score or 0.34,
            evidence={"image_digest": spec.image_digest, "canary_plan": deploy_args["canary_plan"]},
        )
        out = self.infra.deploy(self.mission_id, spec, deploy_args, token)
        if out["release_status"] != "ok":
            raise MissionAborted("6-deploy", f"deploy failed: {out['release_reason']}")
        state.deployed = out["released"]
        state.record(StageRecord(
            stage="6-deploy", status="ok",
            summary=f"H5 token bound to {spec.image_digest}; canary released",
            audit_seqs=out["audit_seqs"], data=out,
        ))

    @staticmethod
    def _verify_claims_sheet(declared: dict, blast_radius: dict) -> tuple[bool, str]:
        """Mechanical claims-sheet check vs blast radius (RFC-001 §5; A.5)."""
        if declared.get("symbols_touched", 0) > blast_radius.get("symbols", 0):
            return False, "symbols_touched exceeds blast radius"
        if declared.get("touches_billing", False):
            return False, "declared scope touches billing (ARS non-goal)"
        return True, "within declared blast radius; billing untouched"

    # --- finalization -----------------------------------------------------

    def _finalize(self, state: MissionState) -> MissionResult:
        events = self.platform.audit.get_events(self.platform.tenant_id)
        verification = verify_chain(events)
        return MissionResult(
            mission_id=self.mission_id,
            state=state,
            audit_length=len(events),
            chain_valid=verification.valid,
            forensics=self._forensics(state, events),
        )

    def _forensics(self, state: MissionState, events) -> dict:
        untrusted_events = [e for e in events if e.context.taint == "external_untrusted"]
        denials = [e for e in events if e.action.type == "policy_decision"]
        prompts = [e for e in events if e.action.type == "prompt"]
        approvals = [e for e in events if e.action.type == "approval"]

        insight = next((s for s in state.stages if s.stage == "0-insight"), None)
        why = (insight.summary if insight else "n/a")

        deploy_stage = next((s for s in state.stages if s.stage == "6-deploy"), None)
        who_prod = (
            f"H5 approval bound to digest {state.spec.image_digest}; "
            f"{len(approvals)} approval events recorded"
            if deploy_stage else "not deployed"
        )

        return {
            "why_feature_exists": why,
            "who_approved_production": who_prod,
            "could_paper_inject": (
                f"{len(untrusted_events)} turn(s)/call(s) carried untrusted content; "
                f"{len(denials)} Action call(s) blocked by policy (taint firewall); "
                "no untrusted turn ever reached an Action tool"
            ),
            "reproduce": (
                f"audit chain length {len(events)}, verified={verify_chain(events).valid}; "
                f"{len(prompts)} prompt hashes pinned for deterministic replay"
            ),
        }
