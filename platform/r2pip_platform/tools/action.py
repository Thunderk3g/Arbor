"""Action-family tools (RFC-001 §3.1). Mutate the world — the firewalled set.

Two enforcement points converge here:
  * The taint firewall (ADR-008) blocks *every* Action tool when the calling
    turn is tainted, regardless of risk class — so ``repo.write`` is denied in a
    turn that just read an untrusted paper.
  * The approval gate (ADR-009) requires a valid single-use token, bound to the
    call's params hash, for ``deploy.release`` (high risk). ``deploy.*`` is also
    role-scoped to the infra agent; ``deploy.rollback`` is pre-authorized.
"""

from __future__ import annotations

import hashlib

from r2pip_gateway import ToolDef


def _short(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def build_action_tools() -> list[ToolDef]:
    def repo_write(args, credential):
        commit = _short(f"{args['repo']}:{args['branch']}:{args['diff']}")
        return {"repo": args["repo"], "branch": args["branch"], "commit": commit}

    def repo_merge(args, credential):
        return {"repo": args["repo"], "branch": args["branch"], "merged_into": "main"}

    def notify_send(args, credential):
        return {"channel": args["channel"], "delivered": True}

    def deploy_release(args, credential):
        return {
            "service": args["service"],
            "digest": args["image_digest"],
            "released": True,
        }

    def deploy_rollback(args, credential):
        return {"service": args["service"], "rolled_back": True}

    return [
        ToolDef(
            name="repo.write", family="action", risk_class="medium",
            input_schema={
                "required": ["repo", "branch", "diff"],
                "properties": {
                    "repo": {"type": "string"},
                    "branch": {"type": "string"},
                    "diff": {"type": "string"},
                },
            },
            handler=repo_write,
        ),
        ToolDef(
            name="repo.merge", family="action", risk_class="medium",
            input_schema={
                "required": ["repo", "branch"],
                "properties": {"repo": {"type": "string"}, "branch": {"type": "string"}},
            },
            handler=repo_merge,
        ),
        ToolDef(
            name="notify.send", family="action", risk_class="low",
            input_schema={
                "required": ["channel", "message"],
                "properties": {"channel": {"type": "string"}, "message": {"type": "string"}},
            },
            handler=notify_send,
        ),
        ToolDef(
            name="deploy.release", family="action", risk_class="high",
            requires_approval=True,
            input_schema={
                "required": ["service", "image_digest"],
                "properties": {
                    "service": {"type": "string"},
                    "image_digest": {"type": "string"},
                    "canary_plan": {"type": "string"},
                },
            },
            handler=deploy_release,
        ),
        ToolDef(
            name="deploy.rollback", family="action", risk_class="high",
            input_schema={"required": ["service"], "properties": {"service": {"type": "string"}}},
            handler=deploy_rollback,
        ),
    ]
