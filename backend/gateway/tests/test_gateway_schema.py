"""Pipeline step 1: schema validation (plus validate_args unit checks)."""

from gateway_helpers import GatewayStack, agent, ctx

from r2pip_gateway import validate_args


def test_missing_required_arg_denied():
    stack = GatewayStack()
    result = stack.gateway.invoke(agent(), "research.search", {}, ctx())
    assert result.status == "denied"
    assert result.reason == "schema_violation:missing_required:query"
    assert stack.handler_calls == []


def test_wrong_type_denied():
    stack = GatewayStack()
    result = stack.gateway.invoke(agent(), "research.search", {"query": 123}, ctx())
    assert result.status == "denied"
    assert result.reason == "schema_violation:type_mismatch:query:expected_string"


def test_enum_violation_denied():
    stack = GatewayStack(budget_limits=None)
    result = stack.gateway.invoke(
        agent(role="infra_agent"),
        "deploy.release",
        {"service": "svc", "revision": "r1", "strategy": "yolo"},
        ctx(),
    )
    assert result.status == "denied"
    assert result.reason == "schema_violation:enum_violation:strategy"


def test_valid_args_pass():
    stack = GatewayStack()
    result = stack.gateway.invoke(
        agent(), "research.search", {"query": "transformers"}, ctx()
    )
    assert result.status == "ok"
    assert result.result["echo"] == {"query": "transformers"}


def test_validate_args_unit():
    schema = {
        "type": "object",
        "required": ["a"],
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "number"},
            "c": {"type": "boolean"},
            "d": {"type": "object"},
            "e": {"type": "array"},
            "f": {"type": "string", "enum": ["x", "y"]},
        },
    }
    assert validate_args({"a": 1}, schema) == []
    assert validate_args({}, schema) == ["missing_required:a"]
    # bool must not satisfy integer/number
    assert validate_args({"a": True}, schema) == ["type_mismatch:a:expected_integer"]
    assert validate_args({"a": 1, "b": True}, schema) == [
        "type_mismatch:b:expected_number"
    ]
    assert validate_args({"a": 1, "b": 2.5, "c": False, "d": {}, "e": []}, schema) == []
    assert validate_args({"a": 1, "f": "z"}, schema) == ["enum_violation:f"]
    assert validate_args({"a": 1, "f": "x"}, schema) == []
