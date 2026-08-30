# `ingestion/` — PDF Parsing, Chunking & Embeddings

Responsible for reading raw PDF bytes and producing structured, searchable representations.

---

## Files

### `pdf_parser.py` — PDF Analysis Engine

**Entry point:** `analyse_pdf(path) → manifest`

Processes a PDF in five passes:

1. **Text extraction** — PyMuPDF `get_text('text')` for native PDF text
2. **Image rendering** — 2× resolution PNG per page (`page-NNN.png`)
3. **Raster image filtering** — extracts embedded images > 40×40 px covering > 1.5% of page
4. **Vector chart detection** — identifies drawing-heavy regions (≥15 primitives, > 5% page area) and crops them
5. **Table extraction** — pdfplumber finds tables; each is serialised as Markdown via `table_to_markdown()`
6. **OCR fallback** — Tesseract `psm 6` TSV mode on image-heavy pages (< 350 chars native text or > 35% image area)

Produces a `manifest` dict saved both to `data/documents/{hash}/manifest.json` and SQLite.

**Content-addressable:** The document archive directory is named by `sha256(file_bytes)`, so the same PDF is never parsed twice.

### `chunking.py` — Structure-Aware Chunking

**Entry point:** `structure_aware_chunks(document_id, pages) → chunks[]`

Three chunk types per page, in priority order:

| Type | Source | Chunk ID format |
|------|--------|-----------------|
| `table` | Markdown table from pdfplumber | `docid:pN:tI` |
| `chart` | Extracted visual summary text | `docid:pN:vI` |
| `narrative` | Sliding-window prose (max 1000 chars, 1-line overlap) | `docid:pN:cI` |

Every chunk is prefixed with `[Slide N: Title]` for retrieval context.

### `embeddings.py` — Embedding Provider

Three implementations behind a common interface (`embed(texts) → list[list[float]]`):

| Class | Backend | When to use |
|-------|---------|-------------|
| `HashEmbeddingProvider` | SHA-256 token hashing (deterministic, offline) | Default / testing |
| `SentenceTransformerEmbeddingProvider` | Local `all-MiniLM-L6-v2` | Better retrieval quality, offline |
| `OllamaEmbeddingProvider` | Ollama `nomic-embed-text` API | GPU-accelerated local embeddings |

**Selected via** `FINSIGHT_EMBEDDINGS` env var (`hash` / `sentence_transformers` / `ollama`).

Ollama provider falls back to `HashEmbeddingProvider` automatically if the API is unreachable.
