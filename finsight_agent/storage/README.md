# `storage/` — SQLite Document & Vector Store

Thread-safe persistence layer used by the pipeline for indexing, retrieval, and run history.

---

## File

### `store.py` — SQLiteResearchStore

**Instantiation:** `SQLiteResearchStore(path='data/finsight.sqlite3')`

Uses a single `threading.Lock` and `check_same_thread=False` so it is safe to share across LangGraph worker threads.

---

## Database Schema

| Table | Columns | Purpose |
|-------|---------|---------|
| `documents` | `id`, `source_path`, `manifest` | One row per unique document (keyed by SHA-256 hash) |
| `pages` | `document_id`, `page`, `payload` | Full page data (text, OCR, tables, visuals) as JSON |
| `sections` | `document_id`, `title`, `start_page`, `end_page`, `kind` | Document structural sections |
| `tables_data` | `document_id`, `page`, `table_index`, `payload` | Individual extracted tables |
| `visuals` | `document_id`, `page`, `visual_index`, `payload` | Image/chart metadata |
| `narratives` | `document_id`, `page`, `block_index`, `payload` | Narrative text blocks |
| `chunks` | `id`, `document_id`, `page`, `text`, `embedding` | Retrieval chunks with stored vectors |
| `runs` | `id`, `document_id`, `status`, `result` | Full pipeline run results |

---

## Methods

| Method | Description |
|--------|-------------|
| `save_analysis(manifest)` | Persist full document manifest (pages, sections, tables, visuals, narratives) |
| `index(doc, path, chunks, vectors)` | Store retrieval chunks and their embeddings |
| `search(doc, vector, limit=4)` | Cosine-similarity search over chunks for a document |
| `save_run(run, doc, status, result)` | Persist final pipeline run result |

---

## Vector Search

Cosine similarity computed in pure Python:

```
score = dot(query, chunk) / (norm(query) × norm(chunk))
```

All chunk vectors for a document are loaded into memory, scored, and sorted. Sufficient for documents up to ~10,000 chunks. For larger corpora, swap the `search()` implementation for a dedicated vector DB.
