# FinSight AI

**Context-Driven Financial Document Intelligence — extracts, validates, and narrates financial data from any company PDF into a publication-grade Geojit-style research report.**

---

## What It Does

Upload any financial PDF (investor presentation, equity research report, earnings release, annual report) and FinSight will:

1. **Understand** the document — company, sector, document type, reporting period
2. **Extract** financial facts using domain-specific rules for Banking, Consumer Tech, Insurance, IT, Manufacturing
3. **Validate** every extracted number with arithmetic cross-checks and source-page citations
4. **Map** results to a structured Geojit report template (zero-hallucination policy)
5. **Generate** a publication-ready PDF with tables, charts, and narrative sections

---

## Quick Start

```bash
# Install dependencies
uv sync

# Process a PDF from the command line
uv run python -m finsight_agent.cli path/to/report.pdf --pdf output/report.pdf

# Start the REST API server
uv run langgraph dev
```

### Upload via Postman / curl

```bash
curl -X POST http://127.0.0.1:2024/api/uploads \
  -F "file=@ICICI_Q2FY26.pdf" | jq .report_url
```

Then open the returned URL to download the PDF report.

---

## Project Structure

```
finsight_agent/
├── core/        # Pydantic contracts, LangGraph state, LLM prompts
├── ingestion/   # PDF parsing, OCR, chunking, vector embeddings
├── analysis/    # Context detection, fact extraction, validation, insights, charts
├── output/      # Template mapping, narrative synthesis, PDF report renderer
├── pipeline/    # LangGraph 12-stage graph and node functions
├── storage/     # Thread-safe SQLite document and vector store
├── api/         # FastAPI REST endpoints (/api/uploads, /api/reports, /api/documents)
└── cli.py       # Command-line runner
```

Each sub-package has its own `README.md` explaining its responsibilities.

---

## Architecture Overview

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full pipeline flow diagram.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/uploads` | Upload PDF → process → return JSON + report URL |
| `GET` | `/api/reports/{run_id}` | Download PDF report |
| `GET` | `/api/documents/{doc_id}` | Get raw document manifest (JSON) |

---

## Design Principles

- **Single Responsibility** — each file has exactly one job
- **Open/Closed** — add a new sector by extending `SECTOR_METRIC_PROFILES` in `context.py`; no existing code changes needed
- **Dependency Inversion** — store and embeddings are injected into the pipeline at build time
- **Zero Hallucination** — fields absent from the source document are explicitly labeled `N/A (Not available in source)` rather than guessed
- **Content-Addressable Uploads** — duplicate PDFs are detected by SHA-256 hash; only one copy is ever stored

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FINSIGHT_EMBEDDINGS` | `hash` | Embedding provider: `hash`, `sentence_transformers`, `ollama` |
| `FINSIGHT_EMBEDDING_MODEL` | model-dependent | Model name for sentence_transformers or ollama |
| `FINSIGHT_LLM_BASE_URL` | — | OpenAI-compatible endpoint for narrative synthesis |
| `FINSIGHT_LLM_MODEL` | — | LLM model name |

Copy `.env.example` to `.env` and fill in your values.

---

## Running Tests

```bash
uv run pytest          # all 10 unit tests
uv run pytest -v       # verbose output
```
