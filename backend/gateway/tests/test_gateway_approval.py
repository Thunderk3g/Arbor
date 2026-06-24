"""Approval gate: real signed single-use tokens from r2pip_approval (RFC §7.3)."""

from gateway_helpers import GatewayStack, agent, ctx

ARGS = {"service": "checkout", "revision": "sha256:deadbeef"}


def test_release_without_token_requires_approval():
    stack = GatewayStack()
    result = stack.gateway.invoke(agent(role="infra_agent"), "deploy.release", ARGS, ctx())
    assert result.status == "denied"
    assert result.reason == "approval_required"


def test_release_with_valid_token_ok():
    stack = GatewayStack()
    token = stack.approval_token_for(ARGS)
    result = stack.gateway.invoke(
        agent(role="infra_agent"), "deploy.release", ARGS, ctx(approval_token=token)
    )
    assert result.status == "ok"
    assert result.result["tool"] == "deploy.release"


def test_replayed_token_denied():
    stack = GatewayStack()
    token = stack.approval_token_for(ARGS)
    first = stack.gateway.invoke(
        agent(role="infra_agent"), "deploy.release", ARGS, ctx(approval_token=token)
    )
    assert first.status == "ok"
    replay = stack.gateway.invoke(
        agent(role="infra_agent"), "deploy.release", ARGS, ctx(approval_token=token)
    )
    assert replay.status == "denied"
    assert replay.reason == "approval_invalid:token_already_used"


def test_token_for_different_args_denied():
    stack = GatewayStack()
    token = stack.approval_token_for({"service": "checkout", "revision": "sha256:OTHER"})
    result = stack.gateway.invoke(
        agent(role="infra_agent"), "deploy.release", ARGS, ctx(approval_token=token)
    )
    assert result.status == "denied"
    assert result.reason == "approval_invalid:params_mismatch"


def test_garbage_token_denied():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(role="infra_agent"),
        "deploy.release",
        ARGS,
        ctx(approval_token="not-a-jwt"),
    )
    assert result.status == "denied"
    assert result.reason == "approval_invalid:invalid_token"
