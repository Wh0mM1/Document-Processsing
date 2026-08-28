# FinSight AI — evidence-grounded LangGraph research agent

## Agent contract

An upload starts a LangGraph run. The run reads the PDF, creates page-preserving chunks, generates and stores embeddings, retrieves evidence for each planned report task, extracts only cited facts, verifies them, and persists the result. The future UI never calls an LLM directly: it starts/resumes a graph run through the LangGraph API.

`upload → ingest → chunk/index → plan → hybrid retrieve/rerank → structured extraction → chart extraction → narrative synthesis → verify → review/export`

Every generated table value, chart point, and paragraph sentence must resolve to `document_id + chunk_id + page + excerpt`. The UI will render the original PDF alongside the generated report; clicking a citation scrolls/highlights the matching source page.

## Output separation

The report contract is deliberately split into `structured_data`, `chart_specs`, and `narrative_sections` in [contracts.py](finsight_agent/contracts.py). This prevents presentation prose from becoming the data source for a chart. A chart may use only independently cited numerical points.

## Embeddings

Use `BAAI/bge-m3` for the production local embedding model: it supports dense, sparse, and ColBERT-style retrieval with 1024 dimensions and up to 8192 tokens. Pair it with `BAAI/bge-reranker-v2-m3`; use hybrid dense + lexical retrieval, then rerank the top candidates. The current deterministic hash provider remains only for offline tests/replay.

## Safe user corrections

A future section-edit request has a `RevisionRequest` contract. Its prompt is treated as a presentation request, never as evidence. The graph retrieves the existing citations and relevant source chunks again, regenerates that one section, verifies every claim, and sends any unsupported requested change to review.

## Run and serve

```bash
cp .env.example .env
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m finsight_agent.cli "/path/to/ICICI Q2FY26.pdf" --output data/icici-run.json
./.venv/bin/pytest -q
langgraph dev
```

`langgraph dev` is the API-first development entry point; it exposes run/thread/assistant APIs for a later frontend. See the [LangGraph CLI documentation](https://docs.langchain.com/langsmith/cli) and the [Academy Studio reference](https://github.com/langchain-ai/langchain-academy/tree/main/module-1/studio).
