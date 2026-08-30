from __future__ import annotations
from typing import Any, TypedDict


class FinSightState(TypedDict, total=False):
    source_path: str
    company_name: str | None
    run_id: str
    document_id: str
    pages: list[dict[str, Any]]
    chunks: list[dict[str, Any]]
    business_context: dict[str, Any]
    research_plan: list[dict[str, Any]]
    retrieved_evidence: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    financial_facts: list[dict[str, Any]]  # Canonical financial facts
    validated_facts: list[dict[str, Any]]  # Arithmetically checked & ranked facts
    guidance: list[dict[str, Any]]  # Forward-looking statements & guidance
    insights: dict[str, Any]  # Structured business insights
    template_mapping: dict[str, Any]  # Geojit semantic template mapping
    structured_data: list[dict[str, Any]]
    chart_specs: list[dict[str, Any]]
    narrative_sections: list[dict[str, Any]]
    llm_summary: dict[str, Any]
    observability_log: list[dict[str, Any]]
    revision_request: dict[str, Any] | None
    quality_flags: list[str]
    retry_count: int
    status: str
    error: str

