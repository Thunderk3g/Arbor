"""Memory-family tools (RFC-001 §3.1, §4). The knowledge-substrate interface.

``graph.write`` is the only way knowledge enters the graph, and it enforces two
invariants mechanically:
  * provenance is mandatory (the gateway's memory rule denies a write whose args
    omit ``provenance``; the ontology validator rejects a node/edge without it);
  * a write tagged ``tier: trusted`` is blocked by the taint firewall when the
    calling turn is tainted, so untrusted context can never mint trusted facts.
``focal.extract`` is the read path the agents brief themselves from.
"""

from __future__ import annotations

from r2pip_focal import InMemoryKnowledgeGraph, focal_extract
from r2pip_gateway import ToolDef
from r2pip_ontology import (
    EdgeInstance,
    NodeInstance,
    Ontology,
    Provenance,
    validate_mutation_batch,
)


def _summary_for(metadata: dict, fallback: str) -> str:
    for key in ("thesis", "statement", "description", "summary"):
        if metadata.get(key):
            return str(metadata[key])
    return fallback


def build_memory_tools(graph: InMemoryKnowledgeGraph, ontology: Ontology) -> list[ToolDef]:
    def graph_write(args, credential):
        provenance = Provenance(**args["provenance"])
        node_models: list[NodeInstance] = []
        for nspec in args.get("nodes", []):
            node_models.append(
                NodeInstance(
                    id=nspec["id"],
                    type=nspec["type"],
                    canonical_name=nspec.get("canonical_name", nspec["id"]),
                    metadata=nspec.get("metadata", {}),
                    confidence=nspec.get("confidence", provenance.confidence),
                    tier=nspec.get("tier", "staging"),
                    provenance=provenance,
                )
            )
        edge_models = [
            EdgeInstance(**espec, provenance=provenance) for espec in args.get("edges", [])
        ]
        report = validate_mutation_batch(node_models, edge_models, ontology)
        if not report["valid"]:
            raise ValueError("ontology_violation: " + "; ".join(report["violations"]))

        written: list[str] = []
        for ni in node_models:
            layer = ontology.node_types_by_name[ni.type].layer
            graph.add_node(
                id=ni.id,
                type=ni.type,
                layer=layer,
                name=ni.canonical_name,
                summary=_summary_for(ni.metadata, ni.canonical_name),
                confidence=ni.confidence,
                tier=ni.tier,
            )
            written.append(ni.id)
        for ei in edge_models:
            graph.add_edge(ei.source_id, ei.target_id, ei.relationship, ei.weight)
        return {"written": len(written), "node_ids": written}

    def graph_query(args, credential):
        node_type = args.get("type")
        layer = args.get("layer")
        ids = set(args["ids"]) if args.get("ids") else None
        out = []
        for nid in sorted(graph.nodes):
            node = graph.nodes[nid]
            if ids is not None and nid not in ids:
                continue
            if node_type and node.type != node_type:
                continue
            if layer and node.layer != layer:
                continue
            out.append(
                {"id": nid, "type": node.type, "layer": node.layer,
                 "name": node.name, "tier": node.tier}
            )
        return {"nodes": out}

    def focal_extract_tool(args, credential):
        fg = focal_extract(
            graph,
            seed_ids=args.get("seed_ids"),
            query_embedding=args.get("query_embedding"),
            purpose=args.get("purpose", "explain"),
            max_nodes=args.get("max_nodes", 150),
            token_budget=args.get("token_budget", 8000),
            include_staging=args.get("include_staging", False),
        )
        return fg.model_dump()

    return [
        ToolDef(
            name="graph.write", family="memory", risk_class="medium",
            # Schema validates shape only; provenance is *enforced* by the
            # gateway's memory_provenance policy rule (RFC-001 §3.3 step 2), so
            # the enforcement lives in one place, not duplicated here.
            input_schema={
                "properties": {
                    "provenance": {"type": "object"},
                    "nodes": {"type": "array"},
                    "edges": {"type": "array"},
                    "tier": {"type": "string", "enum": ["staging", "trusted"]},
                },
            },
            handler=graph_write,
        ),
        ToolDef(
            name="graph.query", family="memory", risk_class="low",
            input_schema={"properties": {"type": {"type": "string"}, "layer": {"type": "string"}}},
            handler=graph_query,
        ),
        ToolDef(
            name="focal.extract", family="memory", risk_class="low",
            input_schema={
                "properties": {
                    "purpose": {"type": "string"},
                    "max_nodes": {"type": "integer"},
                    "token_budget": {"type": "integer"},
                    "include_staging": {"type": "boolean"},
                },
            },
            handler=focal_extract_tool,
        ),
    ]
