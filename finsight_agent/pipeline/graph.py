"""FinSight AI — LangGraph pipeline graph definition.

Wires the 12 pipeline node functions into a sequential StateGraph.
Dependencies (store, embeddings) are injected once at build time via
functools.partial so each node remains a plain function.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from ..core.state import FinSightState
from ..ingestion.embeddings import configured_embeddings
from ..storage.store import SQLiteResearchStore
from . import nodes


def build_graph(store=None, embeddings=None):
    """Build and compile the 12-stage context-driven document intelligence pipeline."""
    store = store or SQLiteResearchStore()
    embeddings = embeddings or configured_embeddings()

    # Bind infrastructure dependencies via closures (LangGraph calls nodes as fn(state))
    wired_nodes = [
        ("ingest_document",      lambda s: nodes.ingest(s,           store=store)),
        ("analyze_context",      nodes.analyze_context),
        ("plan_research",        nodes.plan_research),
        ("chunk_and_index",      lambda s: nodes.chunk_and_index(s,  store=store, embeddings=embeddings)),
        ("retrieve_evidence",    lambda s: nodes.retrieve(s,         store=store, embeddings=embeddings)),
        ("extract_facts",        nodes.extract),
        ("validate_facts",       nodes.validate),
        ("generate_insights",    nodes.insights),
        ("plan_charts",          nodes.plan_charts),
        ("map_template",         nodes.map_template),
        ("synthesize_narrative", nodes.narrate),
        ("finalize",             lambda s: nodes.finalize(s,         store=store)),
    ]

    workflow = StateGraph(FinSightState)
    for name, fn in wired_nodes:
        workflow.add_node(name, fn)

    # Sequential linear pipeline
    node_names = [name for name, _ in wired_nodes]
    workflow.add_edge(START, node_names[0])
    for a, b in zip(node_names, node_names[1:]):
        workflow.add_edge(a, b)
    workflow.add_edge(node_names[-1], END)

    return workflow.compile()


# Module-level compiled graph (used by LangGraph dev server)
graph = build_graph()
