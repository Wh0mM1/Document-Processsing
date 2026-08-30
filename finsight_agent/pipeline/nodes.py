"""LangGraph pipeline node functions.

Each function below is a single, independently-testable pipeline stage.
Inputs and outputs are typed segments of FinSightState (plain dicts at runtime).

Stages:
  1.  ingest          – Parse PDF, save manifest
  2.  analyze_context – Classify company, sector, document type, period
  3.  plan_research   – Build domain-tailored search queries
  4.  chunk_and_index – Chunk document and index vectors
  5.  retrieve        – Semantic vector retrieval per query
  6.  extract         – Context-aware financial fact extraction
  7.  validate        – Arithmetic cross-check and relevance scoring
  8.  insights        – Structured business insight generation
  9.  plan_charts     – Context-aware chart planning
  10. map_template    – Zero-hallucination Geojit template mapping
  11. narrate         – Grounded narrative synthesis
  12. finalize        – Observability log, quality flags, run persistence
"""
from __future__ import annotations

from typing import Any

from ..analysis.charts import plan_contextual_charts
from ..analysis.context import analyze_document_context
from ..analysis.extraction import extract_context_aware_facts
from ..analysis.insights import generate_business_insights
from ..analysis.validation import validate_and_score_facts
from ..core.contracts import (
    BusinessContext,
    BusinessInsights,
    CanonicalFinancialFact,
    ManagementGuidance,
)
from ..ingestion.chunking import structure_aware_chunks
from ..ingestion.pdf_parser import analyse_pdf
from ..output.mapping import map_to_geojit_template
from ..output.narrative import synthesize_grounded_narrative


# ---------------------------------------------------------------------------
# Helper: deserialize state dict to typed Pydantic objects
# ---------------------------------------------------------------------------

def _ctx(state: dict[str, Any]) -> BusinessContext:
    return BusinessContext(**state["business_context"])


def _facts(state: dict[str, Any], key: str = "validated_facts") -> list[CanonicalFinancialFact]:
    return [CanonicalFinancialFact(**f) for f in state.get(key, [])]


def _guidance(state: dict[str, Any]) -> list[ManagementGuidance]:
    return [ManagementGuidance(**g) for g in state.get("guidance", [])]


# ---------------------------------------------------------------------------
# Node 1 — Ingest Document
# ---------------------------------------------------------------------------

def ingest(state: dict[str, Any], *, store) -> dict[str, Any]:
    """Parse PDF and persist manifest to store."""
    manifest = analyse_pdf(state["source_path"])
    store.save_analysis(manifest)
    return {
        "document_id": manifest["document_id"],
        "pages": manifest["pages"],
        "quality_flags": list(manifest["warnings"]),
    }


# ---------------------------------------------------------------------------
# Node 2 — Analyze Document Context
# ---------------------------------------------------------------------------

def analyze_context(state: dict[str, Any]) -> dict[str, Any]:
    """Classify company, sector, document type, reporting period, and primary metrics."""
    context = analyze_document_context(state["pages"])
    return {
        "business_context": context.model_dump(),
        "company_name": context.company,
    }


# ---------------------------------------------------------------------------
# Node 3 — Plan Research Queries
# ---------------------------------------------------------------------------

def plan_research(state: dict[str, Any]) -> dict[str, Any]:
    """Construct domain-specific vector search queries from primary metrics."""
    primary_metrics = state["business_context"].get("primary_metrics", [])
    queries = [
        {
            "output": "structured_data",
            "topic": metric.lower().replace(" ", "_"),
            "query": f"{metric} growth yoy qoq quarterly performance",
        }
        for metric in primary_metrics[:6]
    ]
    queries += [
        {"output": "narrative_sections", "topic": "guidance_outlook",
         "query": "guidance outlook target future growth strategy capex"},
        {"output": "narrative_sections", "topic": "risk_factors",
         "query": "risk challenge headwind asset quality pressure slippage"},
    ]
    return {"research_plan": queries, "retry_count": state.get("retry_count", 0)}


# ---------------------------------------------------------------------------
# Node 4 — Chunk & Index
# ---------------------------------------------------------------------------

def chunk_and_index(state: dict[str, Any], *, store, embeddings) -> dict[str, Any]:
    """Chunk the document into retrieval units and index vector embeddings."""
    chunks = structure_aware_chunks(state["document_id"], state["pages"])
    store.index(
        state["document_id"],
        state["source_path"],
        chunks,
        embeddings.embed([c["text"] for c in chunks]),
    )
    return {"chunks": chunks}


# ---------------------------------------------------------------------------
# Node 5 — Retrieve Evidence
# ---------------------------------------------------------------------------

def retrieve(state: dict[str, Any], *, store, embeddings) -> dict[str, Any]:
    """Retrieve top-k relevant chunks per research query via cosine similarity."""
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    limit = 4 + state.get("retry_count", 0) * 3
    for task in state.get("research_plan", []):
        vector = embeddings.embed([task["query"]])[0]
        for hit in store.search(state["document_id"], vector, limit=limit):
            if hit["chunk_id"] not in seen:
                evidence.append({**hit, "topic": task["topic"]})
                seen.add(hit["chunk_id"])
    return {"retrieved_evidence": evidence}


# ---------------------------------------------------------------------------
# Node 6 — Extract Financial Facts
# ---------------------------------------------------------------------------

def extract(state: dict[str, Any]) -> dict[str, Any]:
    """Context-aware multi-domain extraction of financial facts and guidance."""
    facts, guidance = extract_context_aware_facts(
        state["pages"], _ctx(state), state["document_id"]
    )
    return {
        "financial_facts": [f.model_dump() for f in facts],
        "guidance": [g.model_dump() for g in guidance],
    }


# ---------------------------------------------------------------------------
# Node 7 — Validate & Score Facts
# ---------------------------------------------------------------------------

def validate(state: dict[str, Any]) -> dict[str, Any]:
    """Arithmetic cross-check, deduplication, and relevance scoring."""
    raw_facts = [CanonicalFinancialFact(**f) for f in state.get("financial_facts", [])]
    validated = validate_and_score_facts(raw_facts, _ctx(state))
    return {"validated_facts": [v.model_dump() for v in validated]}


# ---------------------------------------------------------------------------
# Node 8 — Generate Business Insights
# ---------------------------------------------------------------------------

def insights(state: dict[str, Any]) -> dict[str, Any]:
    """Synthesize validated facts into structured thematic business insights."""
    result = generate_business_insights(_facts(state), _guidance(state), _ctx(state))
    return {"insights": result.model_dump()}


# ---------------------------------------------------------------------------
# Node 9 — Plan Charts
# ---------------------------------------------------------------------------

def plan_charts(state: dict[str, Any]) -> dict[str, Any]:
    """Select context-relevant time-series charts (PAT, NII, Revenue, etc.)."""
    chart_specs = plan_contextual_charts(_facts(state), _ctx(state))
    return {"chart_specs": [c.model_dump() for c in chart_specs]}


# ---------------------------------------------------------------------------
# Node 10 — Map to Geojit Template (Zero-Hallucination)
# ---------------------------------------------------------------------------

def map_template(state: dict[str, Any]) -> dict[str, Any]:
    """Map validated facts to Geojit report fields; absent fields are marked N/A."""
    mapping = map_to_geojit_template(_facts(state), _ctx(state), state["pages"])
    return {"template_mapping": mapping.model_dump()}


# ---------------------------------------------------------------------------
# Node 11 — Synthesize Narrative
# ---------------------------------------------------------------------------

def narrate(state: dict[str, Any]) -> dict[str, Any]:
    """Compose grounded executive summary, highlights, concerns, and outlook."""
    insights_obj = BusinessInsights(**state["insights"])
    narrative_result = synthesize_grounded_narrative(
        _ctx(state), insights_obj, _facts(state), _guidance(state)
    )
    narrative_sections = [
        {"title": "Executive Summary", "section_type": "summary",
         "text": narrative_result["executive_summary"], "citations": []},
        {"title": "Positive Highlights & Growth Drivers", "section_type": "positive",
         "text": "\n".join(f"• {p}" for p in narrative_result["positive_highlights"]),
         "citations": []},
        {"title": "Key Concerns & Risk Factors", "section_type": "concerns",
         "text": "\n".join(f"• {c}" for c in narrative_result["concerns"]),
         "citations": []},
        {"title": "Forward-Looking Outlook & Management Guidance", "section_type": "outlook",
         "text": "\n".join(f"• {o}" for o in narrative_result["outlook_and_guidance"]),
         "citations": []},
    ]
    return {"llm_summary": narrative_result, "narrative_sections": narrative_sections}


# ---------------------------------------------------------------------------
# Node 12 — Finalize
# ---------------------------------------------------------------------------

def finalize(state: dict[str, Any], *, store) -> dict[str, Any]:
    """Compile observability log, quality flags, and persist run to store."""
    flags = list(state.get("quality_flags", []))
    validated_facts = state.get("validated_facts", [])
    if len(validated_facts) < 3:
        flags.append("Fewer than three high-confidence financial facts extracted.")

    status = "needs_review" if flags else "complete"

    observability_log = [
        {
            "stage": "document_context_analysis",
            "detected_company": state["business_context"]["company"],
            "detected_sector": state["business_context"]["sector"],
            "detected_document_type": state["business_context"]["document_type"],
            "detected_period": state["business_context"]["period"],
            "business_model": state["business_context"]["business_model"],
            "primary_metrics_selected": state["business_context"]["primary_metrics"],
            "reasoning": state["business_context"]["context_summary"],
        },
        {
            "stage": "fact_extraction_and_validation",
            "raw_facts_count": len(state.get("financial_facts", [])),
            "validated_facts_count": len(validated_facts),
            "guidance_count": len(state.get("guidance", [])),
            "top_extracted_metrics": [
                f"{f['metric_name']} ({f['period']}): {f['value']} {f['unit']}"
                for f in validated_facts[:8]
            ],
        },
        {
            "stage": "template_mapping_zero_hallucination",
            "populated_fields": [
                k for k, v in state["template_mapping"].items()
                if isinstance(v, dict) and v.get("status") == "populated"
            ],
            "missing_fields": state["template_mapping"].get("missing_fields", []),
            "mapping_reasons": {
                k: v.get("mapping_reason")
                for k, v in state["template_mapping"].items()
                if isinstance(v, dict) and "mapping_reason" in v
            },
        },
        {
            "stage": "chart_planning",
            "selected_charts": [
                {"title": c["title"], "metric": c["metric"], "rationale": c.get("rationale")}
                for c in state.get("chart_specs", [])
            ],
        },
    ]

    structured_data = [
        {
            "metric": f["metric_name"],
            "value": f"{f['value']} {f['unit']}".strip(),
            "period": f["period"],
            "validated": f["validation_status"] == "verified",
            "citation": {"page": f["source_page"], "excerpt": f["source_text"]},
        }
        for f in validated_facts
    ]

    result_payload = {
        "run_id": state["run_id"],
        "document_id": state["document_id"],
        "status": status,
        "business_context": state["business_context"],
        "validated_facts": validated_facts,
        "guidance": state.get("guidance", []),
        "insights": state.get("insights", {}),
        "template_mapping": state["template_mapping"],
        "chart_specs": state.get("chart_specs", []),
        "structured_data": structured_data,
        "narrative_sections": state.get("narrative_sections", []),
        "llm_summary": state.get("llm_summary", {}),
        "quality_flags": flags,
        "observability_log": observability_log,
    }

    store.save_run(state["run_id"], state["document_id"], status, result_payload)

    return {
        "status": status,
        "quality_flags": flags,
        "structured_data": structured_data,
        "observability_log": observability_log,
        **{k: state.get(k, {} if k in ("insights", "llm_summary") else [])
           for k in ("business_context", "validated_facts", "guidance",
                     "template_mapping", "chart_specs", "narrative_sections")},
    }
