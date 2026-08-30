# `api/` — FastAPI REST API

HTTP interface for FinSight AI. The API layer **only calls** `build_graph()` and `render_report()` — it contains no domain logic of its own. *(Dependency Inversion Principle)*

---

## File

### `server.py` — FastAPI Application

**ASGI app:** `finsight_agent.api.server:app` (referenced in `langgraph.json`)

---

## Endpoints

### `POST /api/uploads`

Upload a PDF file for processing.

**Request:** `multipart/form-data` with field `file` (`.pdf` only)

**Deduplication:** SHA-256 of file bytes is computed before writing. If the same PDF was uploaded previously, the existing file in `data/uploads/` is reused — no duplicate storage.

**Response:**
```json
{
  "run_id": "uuid-...",
  "status": "complete",
  "document_id": "sha256-hash",
  "business_context": { "company": "...", "sector": "...", "period": "..." },
  "template_mapping": { ... },
  "summary": {
    "validated_facts": [...],
    "narrative_sections": [...],
    "quality_flags": []
  },
  "chart_specs": [...],
  "observability_log": [...],
  "report_url": "/api/reports/{run_id}",
  "document_url": "/api/documents/{document_id}"
}
```

---

### `GET /api/reports/{run_id}`

Download the generated PDF report.

**Response:** `application/pdf` — `finsight-report.pdf`

---

### `GET /api/documents/{document_id}`

Retrieve the raw document manifest (page text, tables, visuals, sections) as JSON.

---

## Running Locally

```bash
# Via LangGraph dev server (recommended — includes Studio UI)
uv run langgraph dev

# Via uvicorn directly
uv run uvicorn finsight_agent.api.server:app --reload --port 8000
```

---

## Postman Example

```
POST http://127.0.0.1:2024/api/uploads
Body → form-data → key: file, value: <select PDF file>
```

The response includes `report_url`. Open `http://127.0.0.1:2024{report_url}` to download the PDF.
