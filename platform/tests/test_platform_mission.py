"""Golden-mission end-to-end tests (the examples/mission-walkthrough.md spec)."""

from r2pip_audit import verify_chain

from r2pip_platform.mission import MissionOrchestrator, rejecting_approver, scripted_approver
from r2pip_platform.mission.orchestrator import MissionOrchestrator as _Orch

from platform_helpers import make_platform, make_spec, run_golden_mission


class TestGoldenMissionHappyPath:
    def test_mission_completes_and_chain_verifies(self):
        _, _, result = run_golden_mission()
        assert result.state.status == "completed"
        assert result.chain_valid is True
        assert result.state.merged is True
        assert result.state.deployed is True

    def test_supervised_risk_mode(self):
        _, _, result = run_golden_mission()
        assert result.state.risk_score == 0.36
        assert result.state.autonomy_mode == "supervised"

    def test_all_six_stages_ok(self):
        _, _, result = run_golden_mission()
        statuses = {s.stage: s.status for s in result.state.stages}
        assert all(v == "ok" for v in statuses.values())
        assert "6-deploy" in statuses

    def test_taint_firewall_blocked_an_action_during_untrusted_turn(self):
        platform, _, result = run_golden_mission()
        build = next(s for s in result.state.stages if s.stage == "3-4-build-validate")
        assert build.data["dev"]["blocked_write_reason"] == "taint_firewall"
        # And it is visible in the audit log: a policy_decision under untrusted taint.
        events = platform.audit.get_events(platform.tenant_id)
        blocked = [
            e for e in events
            if e.action.type == "policy_decision" and e.context.taint == "external_untrusted"
        ]
        assert len(blocked) >= 1

    def test_h5_token_bound_to_image_digest(self):
        _, _, result = run_golden_mission()
        deploy = next(s for s in result.state.stages if s.stage == "6-deploy")
        assert result.state.spec.image_digest in deploy.summary

    def test_forensics_answer_all_four_questions(self):
        _, _, result = run_golden_mission()
        f = result.forensics
        assert set(f) == {
            "why_feature_exists", "who_approved_production",
            "could_paper_inject", "reproduce",
        }
        assert "taint firewall" in f["could_paper_inject"]
        assert "verified=True" in f["reproduce"]

    def test_every_mutation_is_audited_and_chain_intact(self):
        platform, _, result = run_golden_mission()
        events = platform.audit.get_events(platform.tenant_id)
        assert verify_chain(events).valid is True
        # Prompts, tool calls, approvals all present.
        types = {e.action.type for e in events}
        assert {"prompt", "tool_call", "approval", "policy_decision"} <= types


class TestRejectedGatesAbort:
    def test_h1_rejection_aborts_before_deploy(self):
        platform, _, result = run_golden_mission(approver=rejecting_approver("H1"))
        assert result.state.status == "aborted"
        assert "H1" in result.state.abort_reason
        assert result.state.deployed is False
        assert result.chain_valid is True  # audit still consistent

    def test_h2_rejection_aborts(self):
        _, _, result = run_golden_mission(approver=rejecting_approver("H2"))
        assert result.state.status == "aborted" and result.state.deployed is False

    def test_h5_rejection_aborts_after_merge(self):
        _, _, result = run_golden_mission(approver=rejecting_approver("H5"))
        assert result.state.status == "aborted"
        assert "H5" in result.state.abort_reason
        assert result.state.merged is True  # got as far as merge
        assert result.state.deployed is False


class TestClaimsSheetVerification:
    def test_within_blast_radius_passes(self):
        ok, reason = _Orch._verify_claims_sheet(
            {"symbols_touched": 11, "touches_billing": False}, {"symbols": 14}
        )
        assert ok is True and "within" in reason

    def test_symbol_scope_excess_rejected(self):
        ok, reason = _Orch._verify_claims_sheet(
            {"symbols_touched": 99, "touches_billing": False}, {"symbols": 14}
        )
        assert ok is False and "symbols" in reason

    def test_billing_touch_rejected(self):
        ok, reason = _Orch._verify_claims_sheet(
            {"symbols_touched": 3, "touches_billing": True}, {"symbols": 14}
        )
        assert ok is False and "billing" in reason


class TestDeterminism:
    def test_two_runs_produce_identical_audit_length(self):
        _, _, r1 = run_golden_mission()
        _, _, r2 = run_golden_mission()
        assert r1.audit_length == r2.audit_length
        # The opportunity focal graph id is derived from inputs -> identical.
        i1 = next(s for s in r1.state.stages if s.stage == "0-insight")
        i2 = next(s for s in r2.state.stages if s.stage == "0-insight")
        assert i1.data["nodes_in_brief"] == i2.data["nodes_in_brief"]
