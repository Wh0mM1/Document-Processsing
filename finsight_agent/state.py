from typing import TypedDict


class FinSightState(TypedDict, total=False):
    source_path: str
    company_name: str | None
    run_id: str
    document_id: str
    pages: list[dict]
    chunks: list[dict]
    research_plan: list[dict]
    retrieved_evidence: list[dict]
    claims: list[dict]
    financial_facts: list[dict]
    structured_data: list[dict]
    chart_specs: list[dict]
    narrative_sections: list[dict]
    llm_summary: dict
    revision_request: dict | None
    quality_flags: list[str]
    retry_count: int
    status: str
    error: str
