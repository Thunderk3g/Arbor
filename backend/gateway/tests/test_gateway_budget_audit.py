"""Budget governor, handler errors, credential injection, and audit completeness."""

from gateway_helpers import TENANT, GatewayStack, agent, ctx

from r2pip_audit import verify_chain


def test_budget_exhausted_on_third_call():
    stack = GatewayStack(budget_limits={"agent-1": 2})
    for _ in range(2):
        assert (
            stack.gateway.invoke(agent(), "research.search", {"query": "q"}, ctx()).status
            == "ok"
        )
    third = stack.gateway.invoke(agent(), "research.search", {"query": "q"}, ctx())
    assert third.status == "denied"
    assert third.reason == "budget_exhausted"
    # Another principal is unmetered and unaffected.
    other = stack.gateway.invoke(
        agent(principal_id="agent-2"), "research.search", {"query": "q"}, ctx()
    )
    assert other.status == "ok"


def test_handler_error_returns_error_and_audits():
    stack = GatewayStack()
    before = stack.audit.count(TENANT)
    result = stack.gateway.invoke(agent(), "ast.analyze", {"code": "BOOM"}, ctx())
    assert result.status == "error"
    assert result.reason == "handler_error:parser exploded"
    assert stack.audit.count(TENANT) == before + 1
    event = stack.audit.head(TENANT)
    assert event.action.type == "tool_call"
    assert event.action.tool == "ast.analyze"


def test_credential_stub_injected_into_handler():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(principal_id="agent-42"), "research.search", {"query": "q"}, ctx()
    )
    assert result.status == "ok"
    name, _args, credential = stack.handler_calls[-1]
    assert name == "research.search"
    assert credential == "scoped:research.search:agent-42"
    assert result.result["credential"] == "scoped:research.search:agent-42"


def test_audit_completeness_over_mixed_sequence():
    stack = GatewayStack(budget_limits={"agent-1": 3})
    infra = agent(role="infra_agent", principal_id="infra-1")
    release_args = {"service": "svc", "revision": "r1"}
    token = stack.approval_token_for(release_args)

    invokes = [
        stack.gateway.invoke(agent(), "research.search", {"query": "q"}, ctx()),  # ok
        stack.gateway.invoke(agent(), "no.such.tool", {}, ctx()),  # denied unknown
        stack.gateway.invoke(agent(), "research.search", {}, ctx()),  # denied schema
        stack.gateway.invoke(
            infra, "deploy.release", release_args, ctx(taint="external_untrusted")
        ),  # denied taint
        stack.gateway.invoke(agent(), "ast.analyze", {"code": "BOOM"}, ctx()),  # error
        stack.gateway.invoke(
            infra, "deploy.release", release_args, ctx(approval_token=token)
        ),  # ok approved
        stack.gateway.invoke(agent(), "research.search", {"query": "q"}, ctx()),  # ok (3rd consume)
        stack.gateway.invoke(agent(), "graph.write", {"mutations": []}, ctx()),  # denied provenance (no budget consumed)
    ]

    # Exactly one audit event per invoke — including denials and errors.
    assert stack.audit.count(TENANT) == len(invokes)
    events = stack.audit.get_events(TENANT)
    assert verify_chain(events).valid

    # audit_seq returned per result matches the appended event.
    assert [r.audit_seq for r in invokes] == [e.seq for e in events]

    statuses = [r.status for r in invokes]
    expected_types = [
        "tool_call" if s in ("ok", "error") else "policy_decision" for s in statuses
    ]
    assert [e.action.type for e in events] == expected_types
    # All denials are recorded as policy decisions.
    for result, event in zip(invokes, events):
        if result.status == "denied":
            assert event.action.type == "policy_decision"
        assert event.action.params_hash is not None
        assert event.actor.kind == "agent"

    # Taint-denied call carries the untrusted taint in its audit context.
    assert events[3].context.taint == "external_untrusted"
