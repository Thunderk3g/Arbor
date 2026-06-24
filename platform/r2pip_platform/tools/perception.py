"""Perception-family tools (RFC-001 §3.1). Read the outside world.

The gateway tags every perception result ``external_untrusted`` (gateway.py
step 6) regardless of what the handler returns — so any turn that consumes a
perception result is tainted, and the taint firewall (ADR-008) blocks Action
tools for the rest of that turn. ``research.fetch`` returning a paper's text is
exactly the channel a prompt-injection attack would travel; the platform treats
it as DATA, never instructions.
"""

from __future__ import annotations

from r2pip_gateway import ToolDef

# A tiny deterministic "index" standing in for hybrid retrieval over the corpus.
_SEARCH_INDEX = {
    "lhce": [
        {"ref": "arxiv:2401.00001", "title": "LHCE degradation kinetics", "node": "paper-lhce-1"},
    ],
    "cycle-life": [
        {"ref": "arxiv:2401.00001", "title": "LHCE degradation kinetics", "node": "paper-lhce-1"},
    ],
}

_PAPER_TEXT = {
    "arxiv:2401.00001": (
        "Localized high-concentration electrolyte (LHCE) degradation model.\n"
        "Reference implementation (Apache-2.0). Core equation:\n"
        "  cycle_life = k * exp(-Ea / (R * T)) * f(salt_concentration)\n"
        "Reported cycle-life MAE < 5% on held-out cells."
    ),
}

_REPO_FILES = {
    ("svc-pricing", "pricing/price.py"): (
        "def price(contract):\n"
        "    base = contract.kwh * RATE\n"
        "    return base  # TODO: incorporate cycle-life risk premium\n"
    ),
}


def build_perception_tools() -> list[ToolDef]:
    def research_search(args, credential):
        query = args["query"].lower()
        hits: list[dict] = []
        for key, refs in _SEARCH_INDEX.items():
            if key in query:
                hits.extend(refs)
        # de-dup by ref, stable order
        seen, out = set(), []
        for h in hits:
            if h["ref"] not in seen:
                seen.add(h["ref"])
                out.append(h)
        return {"hits": out}

    def research_fetch(args, credential):
        ref = args["ref"]
        return {"ref": ref, "content": _PAPER_TEXT.get(ref, "(not found)")}

    def repo_read(args, credential):
        key = (args["repo"], args["path"])
        return {"repo": args["repo"], "path": args["path"], "content": _REPO_FILES.get(key, "")}

    return [
        ToolDef(
            name="research.search", family="perception", risk_class="low",
            input_schema={"required": ["query"], "properties": {"query": {"type": "string"}}},
            handler=research_search,
        ),
        ToolDef(
            name="research.fetch", family="perception", risk_class="low",
            input_schema={"required": ["ref"], "properties": {"ref": {"type": "string"}}},
            handler=research_fetch,
        ),
        ToolDef(
            name="repo.read", family="perception", risk_class="low",
            input_schema={
                "required": ["repo", "path"],
                "properties": {"repo": {"type": "string"}, "path": {"type": "string"}},
            },
            handler=repo_read,
        ),
    ]
