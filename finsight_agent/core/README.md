# `core/` — Domain Contracts, State & Prompts

This package contains **pure data definitions** — no I/O, no side effects. Everything else in the codebase depends on this package; this package depends on nothing.

---

## Files

### `contracts.py` — Pydantic Data Models

All shared domain types used across the pipeline. Changing a field here affects every stage automatically.

| Model | Purpose |
|-------|---------|
| `BusinessContext` | Detected company, sector, document type, period, business model, primary metrics |
| `CanonicalFinancialFact` | One extracted financial data point with value, unit, period, growth, source page, confidence |
| `ManagementGuidance` | A forward-looking statement (guidance/outlook) separated from historical actuals |
| `BusinessInsights` | Structured lists of growth drivers, profitability trends, risks, data gaps |
| `TemplateField` | A single Geojit report field with value, period, status, and mapping reason |
| `TemplateMapping` | The full Geojit report structure with all thematic tables and brokerage metadata |
| `ChartSpec` / `ChartPoint` | Chart definition with time-series data points |
| `NarrativeSection` | One narrative block (summary / positive / concerns / outlook) |
| `Citation` | Page + excerpt provenance reference |

### `state.py` — LangGraph State Schema

`FinSightState` is a `TypedDict` that flows through the entire LangGraph pipeline. Each node reads from it and returns a partial update dict.

### `prompts.py` — LLM System Prompts

String constants for:
- `REPORT_SYSTEM_PROMPT` — financial analyst persona and grounding rules
- `NARRATIVE_SYNTHESIS_PROMPT` — structured JSON output format for narrative sections
- `REVISION_SYSTEM_PROMPT` — section revision constraints

---

## Design Principle

**Dependency Inversion (DIP)** — all other packages import *from* `core`; `core` never imports from sibling packages.
