from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str = ""
    chunk_id: str = ""
    page: int
    excerpt: str


class BusinessContext(BaseModel):
    company: str
    sector: str
    document_type: str  # "equity_research_report" | "investor_presentation" | "earnings_release" | "annual_report" | "financial_statement" | "other"
    period: str
    document_date: str | None = None
    business_model: str  # "banking" | "consumer_internet" | "insurance" | "nbfc" | "manufacturing" | "technology" | "general"
    primary_metrics: list[str] = Field(default_factory=list)
    reporting_currency_unit: str = "₹ billion"
    has_analyst_estimates: bool = False
    has_target_and_rating: bool = False
    context_summary: str = ""


class CanonicalFinancialFact(BaseModel):
    metric_name: str  # standard canonical name, e.g. "Profit After Tax", "Net Interest Income"
    raw_metric_label: str  # exact label in document, e.g. "Profit after tax excluding treasury"
    value: float | str
    unit: str  # e.g. "₹ billion", "₹ crore", "%", "bps", "x"
    period: str  # e.g. "Q2FY26", "FY25", "Q2-2026"
    period_type: Literal["actual", "estimate", "guidance", "forecast"] = "actual"
    comparison_period: str | None = None
    comparison_value: float | str | None = None
    growth: float | None = None  # explicit or calculated YoY/QoQ growth %
    growth_type: Literal["YoY", "QoQ", ""] | None = None
    category: Literal[
        "profitability",
        "balance_sheet",
        "asset_quality",
        "capital",
        "growth",
        "operational",
        "valuation",
        "guidance"
    ] = "profitability"
    source_document: str = ""
    source_page: int = 1
    source_text: str = ""
    confidence: float = 1.0
    relevance_score: float = 1.0  # 0.0 to 1.0
    validation_status: Literal["verified", "recalculated", "flagged"] = "verified"
    validation_notes: str | None = None


class ManagementGuidance(BaseModel):
    statement: str
    topic: str
    target_period: str | None = None
    source_page: int = 1
    source_excerpt: str = ""


class BusinessInsights(BaseModel):
    growth_drivers: list[dict[str, Any]] = Field(default_factory=list)
    profitability_trends: list[dict[str, Any]] = Field(default_factory=list)
    operational_trends: list[dict[str, Any]] = Field(default_factory=list)
    risk_factors: list[dict[str, Any]] = Field(default_factory=list)
    balance_sheet_strength: list[dict[str, Any]] = Field(default_factory=list)
    business_specific_trends: list[dict[str, Any]] = Field(default_factory=list)
    management_commentary: list[dict[str, Any]] = Field(default_factory=list)
    data_gaps: list[dict[str, Any]] = Field(default_factory=list)


class TemplateField(BaseModel):
    field_name: str
    display_label: str
    value: str
    period: str | None = None
    status: Literal["populated", "not_available_in_source"] = "populated"
    mapping_reason: str = ""


class TemplateMapping(BaseModel):
    company_name: str
    sector: str
    document_type: str
    period: str
    target_price: TemplateField
    recommendation_rating: TemplateField
    current_market_price: TemplateField
    market_cap: TemplateField
    shareholding_summary: TemplateField
    financial_summary_table: list[dict[str, Any]] = Field(default_factory=list)
    balance_sheet_asset_quality_table: list[dict[str, Any]] = Field(default_factory=list)
    portfolio_mix_table: list[dict[str, Any]] = Field(default_factory=list)
    distribution_network_table: list[dict[str, Any]] = Field(default_factory=list)
    subsidiary_performance_table: list[dict[str, Any]] = Field(default_factory=list)
    valuation_multiples: list[dict[str, Any]] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)


class ChartPoint(BaseModel):
    period: str
    value: float | None
    unit: str = ""
    citations: list[Citation] = Field(default_factory=list)


class ChartSpec(BaseModel):
    title: str
    metric: str
    category: str = "trend"
    chart_type: Literal["bar", "line", "grouped_bar"] = "bar"
    rationale: str = ""
    points: list[ChartPoint] = Field(default_factory=list)


class NarrativeSection(BaseModel):
    title: str
    text: str
    section_type: Literal["summary", "positive", "concerns", "outlook", "general"] = "general"
    citations: list[Citation] = Field(default_factory=list)


class StructuredFact(BaseModel):
    label: str
    value: str | None
    period: str | None = None
    status: str = "supported"
    citations: list[Citation] = Field(default_factory=list)


class ReportDraft(BaseModel):
    structured_data: list[StructuredFact]
    chart_specs: list[ChartSpec]
    narrative_sections: list[NarrativeSection]


class RevisionRequest(BaseModel):
    section_id: str
    user_instruction: str = Field(min_length=1, max_length=2000)

