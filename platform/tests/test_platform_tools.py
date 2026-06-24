"""Tool-plane integration tests: every call goes through the real gateway."""

from r2pip_gateway import compute_params_hash

from platform_helpers import agent_principal, ctx, make_platform


class TestPerception:
    def test_results_are_tainted_untrusted(self):
        p = make_platform()
        r = p.gateway.invoke(
            agent_principal(), "research.fetch", {"ref": "arxiv:2401.00001"}, ctx(p)
        )
        assert r.status == "ok"
        # Gateway tags ALL perception output untrusted (gateway.py step 6).
        assert r.result_taint == "external_untrusted"
        assert "LHCE" in r.result["content"]

    def test_search_then_fetch_flow(self):
        p = make_platform()
        s = p.gateway.invoke(agent_principal(), "research.search", {"query": "lhce"}, ctx(p))
        assert s.result["hits"][0]["ref"] == "arxiv:2401.00001"


class TestComputationAllowedUnderTaint:
    def test_code_execute_runs_when_tainted(self):
        p = make_platform()
        dev = agent_principal("dev-7", "developer")
        r = p.gateway.invoke(
            dev, "code.execute",
            {"code": "print(1)", "network": "package_registries"},
            ctx(p, taint="external_untrusted"),
        )
        assert r.status == "ok" and r.result["passed"] is True

    def test_code_execute_rejects_bad_network_enum(self):
        p = make_platform()
        dev = agent_principal("dev-7", "developer")
        r = p.gateway.invoke(
            dev, "code.execute", {"code": "x", "network": "the-whole-internet"}, ctx(p)
        )
        assert r.status == "denied"
        assert "enum_violation:network" in r.reason


class TestMemoryProvenance:
    def test_graph_write_requires_provenance(self):
        p = make_platform()
        r = p.gateway.invoke(
            agent_principal(), "graph.write",
            {"nodes": [{"id": "x", "type": "Opportunity"}]}, ctx(p),
        )
        assert r.status == "denied" and r.reason == "provenance_required"

    def test_graph_write_with_provenance_commits(self):
        p = make_platform()
        prov = {"source_type": "agent_inference", "source_ref": "s", "extractor": "e",
                "confidence": 0.8, "taint": "trusted"}
        r = p.gateway.invoke(
            agent_principal(), "graph.write",
            {"provenance": prov, "tier": "trusted",
             "nodes": [{"id": "opp-x", "type": "Opportunity", "canonical_name": "x",
                        "metadata": {"thesis": "t"}, "confidence": 0.8, "tier": "trusted"}]},
            ctx(p),
        )
        assert r.status == "ok" and r.result["node_ids"] == ["opp-x"]
        assert "opp-x" in p.graph.nodes

    def test_trusted_write_blocked_when_turn_tainted(self):
        p = make_platform()
        prov = {"source_type": "paper", "source_ref": "s", "extractor": "e",
                "confidence": 0.8, "taint": "trusted"}
        r = p.gateway.invoke(
            agent_principal(), "graph.write",
            {"provenance": prov, "tier": "trusted",
             "nodes": [{"id": "opp-y", "type": "Opportunity", "canonical_name": "y",
                        "metadata": {"thesis": "t"}, "tier": "trusted"}]},
            ctx(p, taint="external_untrusted"),
        )
        # Taint firewall blocks trusted-tier writes from untrusted turns.
        assert r.status == "denied" and r.reason == "taint_firewall"

    def test_trusted_tier_hidden_in_node_payload_still_blocked(self):
        # Regression (review Finding 1): omitting the top-level tier but tagging
        # a node trusted must NOT slip a trusted node past the firewall.
        p = make_platform()
        prov = {"source_type": "paper", "source_ref": "s", "extractor": "e",
                "confidence": 0.8, "taint": "trusted"}
        r = p.gateway.invoke(
            agent_principal(), "graph.write",
            {"provenance": prov,
             "nodes": [{"id": "evil", "type": "Opportunity", "canonical_name": "e",
                        "metadata": {"thesis": "t"}, "tier": "trusted"}]},  # no top-level tier
            ctx(p, taint="external_untrusted"),
        )
        assert r.status == "denied" and r.reason == "taint_firewall"
        assert "evil" not in p.graph.nodes

    def test_ontology_violation_surfaces_as_error(self):
        p = make_platform()
        prov = {"source_type": "agent_inference", "source_ref": "s", "extractor": "e",
                "confidence": 0.8, "taint": "trusted"}
        r = p.gateway.invoke(
            agent_principal(), "graph.write",
            {"provenance": prov, "tier": "staging",
             "nodes": [{"id": "z", "type": "NotARealType", "canonical_name": "z"}]},
            ctx(p),
        )
        assert r.status == "error" and "ontology_violation" in r.reason


class TestFocalTool:
    def test_staging_excluded_by_default(self):
        p = make_platform()
        r = p.gateway.invoke(
            agent_principal(), "focal.extract",
            {"seed_ids": ["signal-grid-rfp", "method-lhce"], "purpose": "opportunity_mining"},
            ctx(p),
        )
        ids = [n["id"] for n in r.result["nodes"]]
        assert "paper-poison" not in ids
        assert r.result["taint"] == "trusted"
        assert "staging_tier" in r.result["coverage_note"]

    def test_include_staging_taints_brief(self):
        p = make_platform()
        r = p.gateway.invoke(
            agent_principal(), "focal.extract",
            {"seed_ids": ["method-lhce"], "purpose": "explain", "include_staging": True},
            ctx(p),
        )
        assert r.result["taint"] == "external_untrusted"


class TestActionGates:
    def test_repo_write_blocked_under_taint(self):
        p = make_platform()
        dev = agent_principal("dev-7", "developer")
        r = p.gateway.invoke(
            dev, "repo.write",
            {"repo": "svc-pricing", "branch": "b", "diff": "d"},
            ctx(p, taint="external_untrusted"),
        )
        assert r.status == "denied" and r.reason == "taint_firewall"

    def test_deploy_requires_infra_role(self):
        p = make_platform()
        dev = agent_principal("dev-7", "developer")
        r = p.gateway.invoke(
            dev, "deploy.release", {"service": "svc-pricing", "image_digest": "sha256:x"}, ctx(p)
        )
        assert r.status == "denied" and r.reason == "role_forbidden"

    def test_deploy_requires_approval_token(self):
        p = make_platform()
        infra = agent_principal("infra-1", "infra_agent")
        r = p.gateway.invoke(
            infra, "deploy.release", {"service": "svc-pricing", "image_digest": "sha256:x"}, ctx(p)
        )
        assert r.status == "denied" and r.reason == "approval_required"

    def test_deploy_token_single_use_and_bound(self):
        from r2pip_approval.models import ApprovalDecision

        p = make_platform()
        infra = agent_principal("infra-1", "infra_agent")
        args = {"service": "svc-pricing", "image_digest": "sha256:9f2c"}
        ph = compute_params_hash(args)
        req = p.approval.create_request(
            tenant_id=p.tenant_id, checkpoint="H5", action_type="deploy",
            subject_id="svc-pricing", params_hash=ph, risk_score=0.34,
        )
        token = p.approval.decide(req.id, ApprovalDecision(approver_id="dana", decision="approve")).token

        ok = p.gateway.invoke(infra, "deploy.release", args, ctx(p, approval_token=token))
        assert ok.status == "ok" and ok.result["released"] is True
        replay = p.gateway.invoke(infra, "deploy.release", args, ctx(p, approval_token=token))
        assert replay.status == "denied" and "token_already_used" in replay.reason
        tampered = p.gateway.invoke(
            infra, "deploy.release", {**args, "image_digest": "sha256:EVIL"},
            ctx(p, approval_token=token),
        )
        assert tampered.status == "denied" and "params_mismatch" in tampered.reason
