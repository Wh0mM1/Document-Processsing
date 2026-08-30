# FinSight AI

**Context-Driven Financial Document Intelligence — extracts, validates, and narrates financial data from any company PDF into a publication-grade research report with a modern interactive Web UI.**

---

## Key Features

1. **Intelligent Document Understanding**: Automatically classifies company, sector, document type, and reporting period.
2. **Context-Aware Fact Extraction**: Domain-specific extraction for Banking, Consumer Tech, IT, Manufacturing, Insurance, and Energy sectors.
3. **Strict Validation & Zero Hallucination**: Every number is cross-referenced with arithmetic checks and source-page citations.
4. **Modern Interactive Web UI**: Single-page application with drag-and-drop file upload, in-browser PDF report viewer, original source document preview, and side-by-side verification.
5. **Smart Storage & Deduplication**:
   - Only documents physically present in uploaded storage are displayed.
   - Duplicate uploads automatically override older reports so only a single original file and single latest report are retained.
   - One-click document and report deletion with full database cleanup.
6. **Isolated Docker Containerization**: Complete multi-container orchestration with Docker Compose — runs local LLMs (Ollama) and the application in complete isolation.

---

## Quick Start (Docker & Docker Compose)

The fastest and most isolated way to run FinSight AI (with local LLM models automatically managed) is using **Docker Compose**:

### 1. Launch with Docker Compose

```bash
# Build and start all services in isolation
docker compose up --build
```

### 2. How the Orchestration Works

1. **`ollama` service starts first**: Starts the local Ollama LLM runtime and performs health checks.
2. **`ollama-init` service runs**: Automatically pulls the `llama3.2` text model and `llama3.2-vision` multimodal model into persistent storage.
3. **`app` service starts**: Once models are verified and ready, the FinSight AI backend and modern Web UI start up on port `8000`.

Open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

### 3. Stopping the Services

```bash
# Stop containers (preserves downloaded models and uploaded document data)
docker compose down
```

---

## Local Development (Without Docker)

### 1. Installation & Environment Setup

Clone the repository and synchronize the environment using `uv`:

```bash
# Synchronize virtual environment and install all dependencies
uv sync

# Or if initializing in a fresh clone
uv init --no-workspace
uv sync
```

### 2. Launch the Web Application

Start the FastAPI application and modern Web UI:

```bash
# Start via main entrypoint
python main.py

# Or via uv
uv run python main.py

# Or via uvicorn directly
uvicorn finsight_agent.api.server:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at **[http://localhost:8000](http://localhost:8000)**.
Interactive API documentation (Swagger UI) is available at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### 3. Command-Line Processing (CLI)

Process a PDF directly from the terminal:

```bash
python -m finsight_agent.cli path/to/presentation.pdf --pdf output/report.pdf
```

---

## Running Local LLM & Vision Models (Host Mode)

FinSight AI is built to run **100% locally, privately, and offline** with zero external API costs using open-source models.

### Setting up Local Models with Ollama (Host Mode)

1. **Install Ollama**:
   - macOS / Linux / Windows: Download from [ollama.com](https://ollama.com) or run `brew install ollama` (macOS).

2. **Start the Ollama service**:
   ```bash
   ollama serve
   ```

3. **Pull local models**:
   ```bash
   # Text / Narrative synthesis model
   ollama pull llama3.2          # 3B parameters (fast & lightweight)
   # or: ollama pull qwen2.5:7b

   # Vision / Multimodal chart extraction model (optional)
   ollama pull llama3.2-vision   # 11B multimodal
   # or: ollama pull minicpm-v

   # Local embeddings model (optional)
   ollama pull nomic-embed-text
   ```

4. **Configure `.env`**:
   Copy `.env.example` to `.env` and configure the local endpoint:

   ```env
   # Local LLM Configuration (Ollama / LM Studio / vLLM / LocalAI)
   FINSIGHT_LLM_PROVIDER=openai_compatible
   FINSIGHT_LLM_BASE_URL=http://localhost:11434/v1
   FINSIGHT_LLM_MODEL=llama3.2
   FINSIGHT_VISION_MODEL=llama3.2-vision
   FINSIGHT_LLM_API_KEY=ollama

   # Embeddings Configuration
   FINSIGHT_EMBEDDINGS=hash       # Options: hash (zero-dependency), sentence_transformers, ollama
   ```

> **Note (Offline / Deterministic Mode):** If no local LLM is running (`FINSIGHT_LLM_PROVIDER=none`), FinSight AI runs in deterministic evidence-only mode where facts and tables are extracted purely via rule-based parsers with zero hallucination.

---

## Project Structure

```
├── Dockerfile       # Production multi-stage Dockerfile with Tesseract OCR & PyMuPDF
├── docker-compose.yml # Complete service orchestration (Ollama + Model Puller + App)
├── .dockerignore    # Docker build ignore rules
├── pyproject.toml   # Project dependencies & packaging config
├── requirements.txt # Dependency specifications
├── main.py          # Application launcher
│
├── finsight_agent/
│   ├── core/        # Pydantic data contracts, LangGraph state, system prompts
│   ├── ingestion/   # PDF parsing, raster filtering, vector charts, markdown tables, chunking, embeddings
│   ├── analysis/    # Context detection, table fact extraction, arithmetic validation, trend chart planning
│   ├── output/      # Template mapping, narrative synthesis, ReportLab PDF report renderer
│   ├── pipeline/    # LangGraph pipeline definition and execution nodes
│   ├── storage/     # Thread-safe SQLite document, chunk, and run store
│   ├── api/         # FastAPI REST API & static web serving
│   └── cli.py       # Command-line interface
│
├── static/
│   └── index.html   # Modern Web UI (Tailwind CSS, Lucide icons, Chart.js)
│
└── data/
    ├── uploads/     # Single original source PDF files
    ├── reports/     # Generated publication-ready PDF research reports
    ├── documents/   # Document page assets, vector charts, and manifests
    └── finsight.sqlite3 # Persistent SQLite database
```

---

## API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the interactive Web Application UI |
| `POST` | `/api/uploads` | Upload PDF → process pipeline → return JSON + report URL |
| `GET` | `/api/reports` | List uploaded documents with their single latest generated report |
| `GET` | `/api/reports/{run_id}` | Stream or download (`?download=true`) the generated PDF report |
| `GET` | `/api/reports/{run_id}/summary` | Retrieve full structured JSON summary for a run |
| `GET` | `/api/documents/{doc_id}/pdf` | Stream or download (`?download=true`) the original source PDF for preview |
| `GET` | `/api/documents/{doc_id}` | Retrieve raw document manifest (JSON) |
| `DELETE` | `/api/documents/{doc_id}` | Delete a document, its extracted assets, and its generated report |
| `POST` | `/api/clear-all` | Clear all database records and storage files |
| `GET` | `/api/stats` | Platform analytics and document processing stats |

---

## Running Unit Tests

Run the test suite to verify pipeline integrity, chunking, table extraction, and store operations:

```bash
# Run all tests
PYTHONPATH=. ./.venv/bin/pytest -v

# Or using uv
uv run pytest -v
```
