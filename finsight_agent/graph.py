from langgraph.graph import START, END, StateGraph
from .state import FinSightState
from .store import SQLiteResearchStore
from .embeddings import configured_embeddings
from .nodes import make_nodes


def build_graph(store=None, embeddings=None):
    store = store or SQLiteResearchStore()
    embeddings = embeddings or configured_embeddings()
    ingest, chunk, plan, retrieve, extract, extract_financials, verify, summarize, finalize = make_nodes(
        store, embeddings)
    workflow = StateGraph(FinSightState)
    for name, node in [('ingest_document', ingest), ('chunk_and_index', chunk), ('plan_research', plan), ('retrieve_evidence', retrieve), ('extract_claims', extract), ('extract_financials', extract_financials), ('verify_claims', verify), ('synthesize_with_llm', summarize), ('finalize', finalize)]:
        workflow.add_node(name, node)
    workflow.add_edge(START, 'ingest_document')
    workflow.add_edge('ingest_document', 'chunk_and_index')
    workflow.add_edge('chunk_and_index', 'plan_research')
    workflow.add_edge('plan_research', 'retrieve_evidence')
    workflow.add_edge('retrieve_evidence', 'extract_claims')
    workflow.add_edge('extract_claims', 'extract_financials')
    workflow.add_edge('extract_financials', 'verify_claims')
    workflow.add_edge('verify_claims', 'synthesize_with_llm')
    workflow.add_edge('synthesize_with_llm', 'finalize')
    workflow.add_edge('finalize', END)
    # `langgraph dev`/Agent Server injects its own persistent checkpointer. Keeping
    # the graph unbound here also lets the same definition run in Studio and deploy.
    return workflow.compile()


graph = build_graph()
