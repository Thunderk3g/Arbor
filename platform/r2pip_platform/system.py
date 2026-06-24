"""Platform composition root: wire the six reference slices into one system.

``build_platform`` is the single place the whole stack is assembled. Everything
downstream (agents, mission orchestrator, FastAPI app, demo) takes a ``Platform``
and never constructs services itself — so there is exactly one audit chain, one
signing key, one policy engine, one knowledge graph per tenant.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from r2pip_approval import ApprovalService
from r2pip_approval.keys import generate_keypair
from r2pip_audit import Action, Actor, EventContext, InMemoryAuditStore
from r2pip_focal import InMemoryKnowledgeGraph
from r2pip_gateway import BudgetGovernor, Gateway, PolicyEngine, ToolRegistry
from r2pip_ontology import Ontology, load_ontology

from r2pip_platform.corpus import build_acme_corpus

_ONTOLOGY_PATH = (
    Path(__file__).resolve().parents[2] / "graph" / "ontology" / "schemas" / "ontology-v1.yaml"
)


@dataclass
class Platform:
    """The wired-together R2P-IP reference platform for one tenant."""

    tenant_id: str
    audit: InMemoryAuditStore
    approval: ApprovalService
    public_key: object  # Ed25519PublicKey, for token decoding in tests
    graph: InMemoryKnowledgeGraph
    ontology: Ontology
    registry: ToolRegistry
    policy: PolicyEngine
    budget: BudgetGovernor
    gateway: Gateway

    # --- convenience used by the orchestrator -----------------------------

    def audit_event(
        self,
        *,
        actor: Actor,
        action: Action,
        mission_id: Optional[str] = None,
        task_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        taint: str = "trusted",
    ) -> int:
        """Append one event the orchestrator itself authors (prompt/approval),
        returning its sequence number. Tool calls are audited by the gateway."""
        event = self.audit.append(
            tenant_id=self.tenant_id,
            actor=actor,
            action=action,
            context=EventContext(
                mission_id=mission_id, task_id=task_id, trace_id=trace_id, taint=taint
            ),
        )
        return event.seq


def build_platform(
    tenant_id: str = "acme-energy",
    *,
    graph: Optional[InMemoryKnowledgeGraph] = None,
    token_ttl_seconds: int = 900,
) -> Platform:
    """Assemble a Platform. Tools are registered lazily here to avoid an import
    cycle (tools -> system -> tools)."""
    from r2pip_platform.tools import build_registry  # local import: cycle break

    private_key, public_key = generate_keypair()
    approval = ApprovalService(private_key, token_ttl_seconds=token_ttl_seconds)
    audit = InMemoryAuditStore()
    kg = graph if graph is not None else build_acme_corpus()
    ontology = load_ontology(_ONTOLOGY_PATH)

    registry = build_registry(kg, ontology)
    policy = PolicyEngine(approval_verifier=approval.verify)
    budget = BudgetGovernor()
    gateway = Gateway(registry, policy, budget, audit)

    return Platform(
        tenant_id=tenant_id,
        audit=audit,
        approval=approval,
        public_key=public_key,
        graph=kg,
        ontology=ontology,
        registry=registry,
        policy=policy,
        budget=budget,
        gateway=gateway,
    )
