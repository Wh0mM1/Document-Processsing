# `analysis/` — Context Detection, Extraction, Validation, Insights & Charts

Five single-responsibility modules that transform raw page text into validated, structured financial intelligence.

---

## Files

### `context.py` — Document Understanding Stage

**Entry point:** `analyze_document_context(pages) → BusinessContext`

Answers five questions before any financial extraction happens:

| Question | How |
|----------|-----|
| **What company?** | Regex for common suffixes (Limited, Ltd, Bank, Corp…) in first 6 pages |
| **What sector?** | Keyword frequency scoring across 4 domains — winner by max score ≥ 3 |
| **What document type?** | Signature phrases: "target price" → research report, "investor presentation" → pres |
| **What period?** | `Q[1-4]-FY\d{2,4}` regex, most frequent match in first 3 pages |
| **What metrics matter?** | `SECTOR_METRIC_PROFILES` dict — maps `business_model` to a ranked list of KPIs |

**Adding a new sector:** Add one entry to `SECTOR_METRIC_PROFILES` in `context.py`. No other code changes needed. *(Open/Closed Principle)*

---

### `extraction.py` — Financial Fact Extraction Engine

**Entry point:** `extract_context_aware_facts(pages, context, doc_id) → (facts[], guidance[])`

Three extraction layers in priority order:

1. **`extract_table_facts()`** — pdfplumber table grids parsed as multi-period column tables. Strips footnote superscripts (`1\n215.29` → `215.29`).
2. **Page-specific block parsers** — for known complex layouts (banking pages 13, 15, 16, 18) where table cells don't parse cleanly. Pinpoints correct `Sep 30, 2025` column values.
3. **`extract_prose_facts_and_guidance()`** — line-by-line regex against `METRIC_DEFINITIONS`. Distinguishes absolute monetary amounts from growth percentages.

**METRIC_DEFINITIONS** — a list of `(canonical_name, category, default_unit, regex_pattern)` tuples covering Banking, Consumer Tech, Insurance, IT, and Manufacturing metrics.

**Foreign subsidiary demotion:** Pages ≥ 53 in banking documents get `relevance_score = 0.40` for overlapping parent metrics.

---

### `validation.py` — Arithmetic Cross-Check & Scoring

**Entry point:** `validate_and_score_facts(facts, context) → facts[]`

- Recalculates YoY / QoQ growth: `((current − prior) / prior) × 100%`
- Flags arithmetic mismatches between stated and computed growth
- Deduplicates: table-sourced facts win over prose-sourced facts for the same metric
- Scores recency: `Sep 30, 2025` > `Jun 30, 2025` > `Sep 30, 2024`
- Sets `validation_status`: `verified` | `recalculated` | `flagged`

---

### `insights.py` — Business Insight Generator

**Entry point:** `generate_business_insights(facts, guidance, context) → BusinessInsights`

Synthesises validated facts into seven thematic buckets:

| Bucket | What it captures |
|--------|-----------------|
| `growth_drivers` | Top-line revenue / NII / GOV growth with YoY % |
| `profitability_trends` | PAT, EBITDA, NIM, RoA — improvement or contraction |
| `balance_sheet_strength` | Deposits, advances, net worth, CET1 capital |
| `risk_factors` | GNPA, NNPA, credit cost, slippages, headwinds |
| `business_specific_trends` | Dark stores, branches, ATMs, vehicle loans |
| `management_commentary` | Forward-looking guidance extracted separately |
| `data_gaps` | Expected domain KPIs not found in source |

---

### `charts.py` — Context-Aware Chart Planner

**Entry point:** `plan_contextual_charts(facts, context) → ChartSpec[]`

Selects up to 4 charts based on `business_model`:

| Sector | Charts |
|--------|--------|
| Banking | PAT Trend, NII Trend, Total Advances Trend, Net NPA Ratio Trend |
| Consumer / Tech | Revenue Trend, EBITDA Trend, GOV/NOV Trend, PAT Trend |
| General | Revenue Trend, EBITDA Trend, Net Profit Trend |

Each `ChartSpec` contains `ChartPoint(period, value, unit)` time-series data built from validated facts across all periods.
