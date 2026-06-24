"""Policy rules: families, taint firewall (ADR-008), provenance, role scoping."""

from gateway_helpers import GatewayStack, agent, ctx


def test_perception_allowed_for_any_agent_and_result_tainted():
    stack = GatewayStack()
    for role in ("developer_agent", "infra_agent", "qa_agent"):
        result = stack.gateway.invoke(
            agent(role=role, principal_id=f"agent-{role}"),
            "research.search",
            {"query": "q"},
            ctx(),
        )
        assert result.status == "ok"
        # Perception output is attacker-influenceable by definition.
        assert result.result_taint == "external_untrusted"


def test_computation_allowed_and_keeps_context_taint():
    stack = GatewayStack()
    result = stack.gateway.invoke(agent(), "ast.analyze", {"code": "x = 1"}, ctx())
    assert result.status == "ok"
    assert result.result_taint == "trusted"


def test_unknown_tool_denied():
    stack = GatewayStack()
    result = stack.gateway.invoke(agent(), "no.such.tool", {}, ctx())
    assert result.status == "denied"
    assert result.reason == "unknown_tool"


def test_taint_firewall_blocks_action_even_with_valid_token():
    stack = GatewayStack()
    args = {"service": "svc", "revision": "sha256:abc"}
    token = stack.approval_token_for(args)
    result = stack.gateway.invoke(
        agent(role="infra_agent"),
        "deploy.release",
        args,
        ctx(taint="external_untrusted", approval_token=token),
    )
    assert result.status == "denied"
    assert result.reason == "taint_firewall"
    # The token was never presented to the verifier, so it remains unconsumed
    # and still works once the context is trusted again.
    clean = stack.gateway.invoke(
        agent(role="infra_agent"), "deploy.release", args, ctx(approval_token=token)
    )
    assert clean.status == "ok"


def test_taint_firewall_blocks_trusted_tier_memory_write():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(),
        "graph.write",
        {"mutations": [], "provenance": {"source_type": "paper"}, "tier": "trusted"},
        ctx(taint="external_untrusted"),
    )
    assert result.status == "denied"
    assert result.reason == "taint_firewall"


def test_taint_firewall_blocks_trusted_tier_hidden_in_node_payload():
    # Regression: an untrusted turn must not mint a trusted-tier node by hiding
    # tier inside the payload while omitting the top-level tier hint (ADR-008).
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(),
        "graph.write",
        {
            "mutations": [{"op": "upsert_node", "tier": "trusted"}],
            "provenance": {"source_type": "paper"},
            # NOTE: no top-level "tier" key
        },
        ctx(taint="external_untrusted"),
    )
    assert result.status == "denied"
    assert result.reason == "taint_firewall"


def test_taint_firewall_allows_staging_memory_write():
    # A staging-tier write from an untrusted turn is the *intended* path and
    # must still be permitted (untrusted facts land in staging for promotion).
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(),
        "graph.write",
        {
            "mutations": [{"op": "upsert_node", "tier": "staging"}],
            "provenance": {"source_type": "paper", "source_ref": "arxiv:1"},
            "tier": "staging",
        },
        ctx(taint="external_untrusted"),
    )
    assert result.status == "ok"


def test_taint_firewall_keeps_perception_available():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(), "research.search", {"query": "q"}, ctx(taint="external_untrusted")
    )
    assert result.status == "ok"
    assert result.result_taint == "external_untrusted"


def test_graph_write_without_provenance_denied():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(), "graph.write", {"mutations": [], "tier": "staging"}, ctx()
    )
    assert result.status == "denied"
    assert result.reason == "provenance_required"


def test_graph_write_with_provenance_allowed():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(),
        "graph.write",
        {
            "mutations": [{"op": "upsert_node"}],
            "provenance": {"source_type": "paper", "source_ref": "arxiv:1"},
            "tier": "staging",
        },
        ctx(),
    )
    assert result.status == "ok"
    assert result.result_taint == "trusted"


def test_deploy_release_wrong_role_forbidden():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(role="developer_agent"),
        "deploy.release",
        {"service": "svc", "revision": "r1"},
        ctx(),
    )
    assert result.status == "denied"
    assert result.reason == "role_forbidden"


def test_deploy_rollback_preauthorized_for_infra_agent():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(role="infra_agent"), "deploy.rollback", {"service": "svc"}, ctx()
    )
    assert result.status == "ok"
    assert result.result["tool"] == "deploy.rollback"


def test_deploy_rollback_wrong_role_forbidden():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(role="qa_agent"), "deploy.rollback", {"service": "svc"}, ctx()
    )
    assert result.status == "denied"
    assert result.reason == "role_forbidden"
