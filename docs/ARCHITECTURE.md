# docs/ARCHITECTURE.md — FinSight AI Pipeline

## End-to-End Pipeline Flow

Every uploaded PDF travels through 12 sequential stages inside a LangGraph StateGraph.

```
PDF File
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: INGEST                           [ingestion/]     │
│  • Parse PDF with PyMuPDF + pdfplumber                      │
│  • Extract text, tables (Markdown), images, vector charts   │
│  • Run OCR (Tesseract) on image-heavy pages                 │
│  • Hash file → content-addressable archive in data/documents│
│  • Save manifest.json to disk + SQLite                      │
└──────────────────────────┬──────────────────────────────────┘
                           │ pages[], warnings[]
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: ANALYZE CONTEXT                  [analysis/]      │
│  • Detect company name (regex heuristics)                   │
│  • Score domain signals → sector + business_model           │
│    (Banking / Consumer Tech / Insurance / IT / General)     │
│  • Classify document type (research report / investor pres  │
│    / earnings release / annual report / financial statement)│
│  • Extract reporting period (Q2-2026, FY25, H1-2026…)       │
│  • Select domain-specific primary_metrics list              │
└──────────────────────────┬──────────────────────────────────┘
                           │ BusinessContext
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 3: PLAN RESEARCH                    [pipeline/]      │
│  • Build one search query per primary metric                │
│  • Add cross-cutting queries for guidance and risk factors  │
└──────────────────────────┬──────────────────────────────────┘
                           │ research_plan[]
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 4: CHUNK & INDEX                    [ingestion/]     │
│  • Split pages into table chunks, chart summaries, and      │
│    sliding-window narrative chunks (max 1000 chars)         │
│  • Generate vector embeddings (hash / sentence-transformers │
│    / Ollama — configured via FINSIGHT_EMBEDDINGS env var)   │
│  • Store chunk text + embedding in SQLite chunks table      │
└──────────────────────────┬──────────────────────────────────┘
                           │ chunks[]
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 5: RETRIEVE EVIDENCE                [storage/]       │
│  • Cosine similarity search per research query              │
│  • Return top-k relevant chunks per topic                   │
└──────────────────────────┬──────────────────────────────────┘
                           │ retrieved_evidence[]
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 6: EXTRACT FACTS                    [analysis/]      │
│  • Multi-domain METRIC_DEFINITIONS regex patterns           │
│  • Page-specific block parsers for complex table layouts    │
│    (e.g., ICICI P15 loan portfolio, P16 retail breakdown,   │
│    P18 NPA trends, P47 branch/ATM network)                  │
│  • Footnote superscript stripping (1\n215.29 → 215.29)      │
│  • Monetary vs. percentage disambiguation                   │
│  • Foreign subsidiary page demotion (relevance 0.40)        │
│  • Extracts ManagementGuidance from forward-looking prose   │
└──────────────────────────┬──────────────────────────────────┘
                           │ financial_facts[], guidance[]
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 7: VALIDATE & SCORE                 [analysis/]      │
│  • Arithmetic cross-check: recalculate YoY / QoQ growth     │
│    and compare against stated values                        │
│  • Deduplication across sources (table > prose precedence)  │
│  • Period recency scoring (latest period wins)              │
│  • Relevance scoring relative to BusinessContext            │
│  • validation_status: "verified" | "recalculated" | "flagged│
└──────────────────────────┬──────────────────────────────────┘
                           │ validated_facts[]
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 8: GENERATE INSIGHTS                [analysis/]      │
│  • Synthesize facts into BusinessInsights:                  │
│    growth_drivers, profitability_trends, balance_sheet,     │
│    risk_factors, business_specific_trends, data_gaps        │
└──────────────────────────┬──────────────────────────────────┘
                           │ BusinessInsights
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 9: PLAN CHARTS                      [analysis/]      │
│  • Selects 4 context-relevant time-series charts            │
│  • Banking: PAT, NII, Total Advances, NPA Ratio Trend       │
│  • Consumer: Revenue, EBITDA, GOV/NOV, PAT Trend            │
│  • Collects period→value points across all validated facts  │
└──────────────────────────┬──────────────────────────────────┘
                           │ ChartSpec[]
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 10: MAP TEMPLATE (Zero Hallucination) [output/]      │
│  • Maps facts to Geojit report fields                       │
│  • Brokerage fields (Target Price, Rating, CMP, Market Cap) │
│    populated only for equity_research_report documents      │
│  • All absent fields → status: "not_available_in_source"    │
│    value: "N/A (Not available in source)"                   │
│  • Builds 5 themed financial tables                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ TemplateMapping
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 11: SYNTHESIZE NARRATIVE            [output/]        │
│  • Composes executive summary, positive highlights,         │
│    key concerns, and management outlook                     │
│  • Uses LLM (OpenAI-compatible) if configured               │
│  • Falls back to deterministic template synthesis from      │
│    BusinessInsights (no LLM needed)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ narrative_sections[]
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 12: FINALIZE                        [pipeline/]      │
│  • Compile observability log (all 4 reasoning stages)       │
│  • Check quality flags (< 3 facts → needs_review)           │
│  • Persist run result to SQLite runs table                  │
│  • Return complete result payload                           │
└──────────────────────────┬──────────────────────────────────┘
                           │ run result
                           ▼
              ┌────────────────────────┐
              │  render_report()        │
              │  ReportLab PDF Generator│
              │  [output/report.py]     │
              └────────────┬───────────┘
                           │
                           ▼
                   finsight-report.pdf
```

---

## Data Flow — Key Types

```
PDF path
  → analyse_pdf()              → manifest (pages, tables, visuals)
  → analyze_document_context() → BusinessContext
  → extract_context_aware_facts() → CanonicalFinancialFact[]
  → validate_and_score_facts() → CanonicalFinancialFact[] (scored)
  → generate_business_insights() → BusinessInsights
  → plan_contextual_charts()   → ChartSpec[]
  → map_to_geojit_template()   → TemplateMapping
  → synthesize_grounded_narrative() → narrative_sections[]
  → render_report()            → PDF file
```

---

## Zero-Hallucination Policy

Any field not present in the source document (e.g., Target Price in an investor presentation) is **never guessed**. Instead:

```json
{
  "field_name": "target_price",
  "value": "N/A (Not available in source)",
  "status": "not_available_in_source",
  "mapping_reason": "Source is an investor_presentation; target price is only disclosed in equity research reports"
}
```

---

## Content-Addressable Storage

```
Upload PDF
   │
   ├─ sha256(content) → doc_hash
   │
   ├─ data/uploads/{doc_hash}.pdf   ← one file per unique PDF
   │
   └─ data/documents/{doc_hash}/    ← one analysis archive per unique PDF
        ├── original.pdf
        ├── manifest.json
        ├── page-001.png ... page-NNN.png
        └── p001-image-01.png ...
```

If the same PDF is uploaded 10 times, exactly one file is stored.
