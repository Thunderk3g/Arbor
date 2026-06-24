"""Runnable end-to-end demo: ``python -m r2pip_platform`` (or ...demo).

Executes the golden mission MSN-4413 against a freshly built platform and prints
a human-readable trace: the focal opportunity path, every stage and its HITL
gate, the taint-firewall block, the H5-bound deploy, and the four forensic
questions the audit chain can answer. Pure stdlib output, ASCII-only so it is
safe on any console.
"""

from __future__ import annotations

import sys
from typing import TextIO

from r2pip_platform import MissionSpec, build_platform
from r2pip_platform.corpus import OPPORTUNITY_SEEDS
from r2pip_platform.mission import MissionOrchestrator, scripted_approver
from r2pip_platform.types import MissionResult


def _rule(out: TextIO, char: str = "-") -> None:
    out.write(char * 72 + "\n")


def run_demo(out: TextIO = sys.stdout) -> MissionResult:
    platform = build_platform()
    spec = MissionSpec(
        tenant_id=platform.tenant_id,
        title="Add electrolyte cycle-life prediction to acme's pricing API",
        opportunity_seed_ids=OPPORTUNITY_SEEDS,
    )
    orch = MissionOrchestrator(platform, scripted_approver)
    result = orch.run(spec)

    _rule(out, "=")
    out.write("R2P-IP REFERENCE PLATFORM  |  Golden Mission MSN-4413\n")
    out.write(f"tenant={platform.tenant_id}  graph_nodes={len(platform.graph.nodes)}  "
              f"tools={len(platform.registry.list())}\n")
    _rule(out, "=")
    out.write(f"mission: {spec.title}\n")
    out.write(f"status:  {result.state.status.upper()}  "
              f"(risk R={result.state.risk_score}, mode={result.state.autonomy_mode})\n")
    out.write(f"merged={result.state.merged}  deployed={result.state.deployed}\n\n")

    insight = next((s for s in result.state.stages if s.stage == "0-insight"), None)
    if insight:
        out.write("FOCAL OPPORTUNITY SWEEP (staging-tier poison defended):\n")
        out.write("  " + insight.data.get("focal_path", "") + "\n\n")

    out.write("STAGES & HITL GATES:\n")
    for s in result.state.stages:
        out.write(f"  [{s.status.upper():8}] {s.stage}: {s.summary}\n")
    out.write("\n")

    out.write("WHAT THE AUDIT TRAIL ANSWERS:\n")
    for key, label in (
        ("why_feature_exists", "Why does this feature exist?"),
        ("who_approved_production", "Who approved production?"),
        ("could_paper_inject", "Could the paper have injected anything?"),
        ("reproduce", "Reproduce it?"),
    ):
        out.write(f"  - {label}\n      {result.forensics[key]}\n")
    out.write("\n")

    _rule(out)
    out.write(f"AUDIT: {result.audit_length} hash-chained events, "
              f"chain_valid={result.chain_valid}\n")
    _rule(out)
    return result


def main() -> int:
    # Make stdout UTF-8 tolerant where the console allows it; output is ASCII.
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    result = run_demo()
    return 0 if result.state.status == "completed" and result.chain_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
