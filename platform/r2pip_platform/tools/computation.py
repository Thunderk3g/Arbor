"""Computation-family tools (RFC-001 §3.1). Pure analysis over code/specs.

Computation tools never touch the outside world and are permitted even when the
turn is tainted — that is what lets a developer keep working in the sandbox on
untrusted paper content while Action tools are firewalled off (walkthrough §8-9).
``code.execute`` stands in for the gVisor sandbox: deterministic, no real I/O.
"""

from __future__ import annotations

from r2pip_gateway import ToolDef


def build_computation_tools() -> list[ToolDef]:
    def ast_analyze(args, credential):
        # Deterministic stand-in for the tree-sitter service.
        return {"repo": args["repo"], "symbols": 14, "language": "python"}

    def deps_graph(args, credential):
        return {"repo": args["repo"], "services": 1, "dependencies": ["numpy"]}

    def blast_analyze(args, credential):
        # The structural inputs to the Head Engineer's risk score (RFC §5 stage 6).
        return {
            "repo": args["repo"],
            "blast_radius": {
                "symbols": 14,
                "services": 1,
                "untested_fraction": 0.07,
                "touches_billing": False,
            },
        }

    def code_execute(args, credential):
        # Sandbox stand-in: "runs" the candidate and reports a green result.
        network = args.get("network", "none")
        return {"passed": True, "network": network, "stdout": "28 passed in 0.4s"}

    def spec_validate(args, credential):
        ars = args["ars"]
        issues = []
        if not ars.get("acceptance_criteria"):
            issues.append("no acceptance criteria")
        if not ars.get("non_goals"):
            issues.append("no non-goals declared")
        return {"valid": not issues, "issues": issues}

    def test_generate(args, credential):
        return {"target": args["target"], "tests_added": 28, "mutation_score": 0.74}

    return [
        ToolDef(
            name="ast.analyze", family="computation", risk_class="low",
            input_schema={"required": ["repo"], "properties": {"repo": {"type": "string"}}},
            handler=ast_analyze,
        ),
        ToolDef(
            name="deps.graph", family="computation", risk_class="low",
            input_schema={"required": ["repo"], "properties": {"repo": {"type": "string"}}},
            handler=deps_graph,
        ),
        ToolDef(
            name="blast.analyze", family="computation", risk_class="low",
            input_schema={"required": ["repo"], "properties": {"repo": {"type": "string"}}},
            handler=blast_analyze,
        ),
        ToolDef(
            name="code.execute", family="computation", risk_class="medium",
            input_schema={
                "required": ["code"],
                "properties": {
                    "code": {"type": "string"},
                    "network": {"type": "string", "enum": ["none", "package_registries"]},
                },
            },
            handler=code_execute,
        ),
        ToolDef(
            name="spec.validate", family="computation", risk_class="low",
            input_schema={"required": ["ars"], "properties": {"ars": {"type": "object"}}},
            handler=spec_validate,
        ),
        ToolDef(
            name="test.generate", family="computation", risk_class="low",
            input_schema={"required": ["target"], "properties": {"target": {"type": "string"}}},
            handler=test_generate,
        ),
    ]
