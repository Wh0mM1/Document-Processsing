# `pipeline/` — LangGraph Graph & Node Functions

Wires the 12 processing stages into a compiled LangGraph `StateGraph`.

---

## Files

### `nodes.py` — Pipeline Node Functions

Each function is a **standalone, independently-testable** pipeline stage. No closures, no hidden state.

| Function | Reads from State | Writes to State |
|----------|-----------------|----------------|
| `ingest(state, *, store)` | `source_path` | `document_id`, `pages`, `quality_flags` |
| `analyze_context(state)` | `pages` | `business_context`, `company_name` |
| `plan_research(state)` | `business_context` | `research_plan`, `retry_count` |
| `chunk_and_index(state, *, store, embeddings)` | `document_id`, `pages` | `chunks` |
| `retrieve(state, *, store, embeddings)` | `research_plan`, `document_id` | `retrieved_evidence` |
| `extract(state)` | `pages`, `business_context`, `document_id` | `financial_facts`, `guidance` |
| `validate(state)` | `financial_facts`, `business_context` | `validated_facts` |
| `insights(state)` | `validated_facts`, `guidance`, `business_context` | `insights` |
| `plan_charts(state)` | `validated_facts`, `business_context` | `chart_specs` |
| `map_template(state)` | `validated_facts`, `business_context`, `pages` | `template_mapping` |
| `narrate(state)` | `insights`, `validated_facts`, `guidance`, `business_context` | `llm_summary`, `narrative_sections` |
| `finalize(state, *, store)` | all keys | `status`, `quality_flags`, `observability_log`, `structured_data` |

**Helper functions:**

```python
_ctx(state)         # → BusinessContext (deserialises state["business_context"])
_facts(state, key)  # → list[CanonicalFinancialFact]
_guidance(state)    # → list[ManagementGuidance]
```

These helpers exist once and are reused by every node that needs Pydantic objects — no repeated `BusinessContext(**state["business_context"])` boilerplate. *(DRY Principle)*

**Dependency injection:** Nodes that need `store` or `embeddings` receive them via keyword-only arguments. The graph binds them with `functools.partial` at build time — not inside closures. *(Dependency Inversion Principle)*

---

### `graph.py` — StateGraph Definition

**Entry point:** `build_graph(store=None, embeddings=None) → CompiledGraph`

```python
from finsight_agent.pipeline.graph import build_graph
graph = build_graph()
result = graph.invoke({"source_path": "path/to/file.pdf", "run_id": "..."})
```

- Edges are built programmatically from the ordered `wired_nodes` list — adding a stage is one line
- `graph` module-level variable is the pre-compiled instance used by `uv run langgraph dev`

---

## Extending the Pipeline

To add a new stage between `validate` and `insights`:

1. Write `def my_stage(state) -> dict` in `nodes.py`
2. Insert it into `wired_nodes` in `graph.py`

No other files need to change.
