"""Core domain contracts, state schema, and LLM prompt strings."""
from .contracts import (
    BusinessContext,
    CanonicalFinancialFact,
    ManagementGuidance,
    BusinessInsights,
    TemplateField,
    TemplateMapping,
    ChartPoint,
    ChartSpec,
    NarrativeSection,
    StructuredFact,
    ReportDraft,
    Citation,
    RevisionRequest,
)
from .state import FinSightState
from .prompts import REPORT_SYSTEM_PROMPT, NARRATIVE_SYNTHESIS_PROMPT, REVISION_SYSTEM_PROMPT

__all__ = [
    "BusinessContext",
    "CanonicalFinancialFact",
    "ManagementGuidance",
    "BusinessInsights",
    "TemplateField",
    "TemplateMapping",
    "ChartPoint",
    "ChartSpec",
    "NarrativeSection",
    "StructuredFact",
    "ReportDraft",
    "Citation",
    "RevisionRequest",
    "FinSightState",
    "REPORT_SYSTEM_PROMPT",
    "NARRATIVE_SYNTHESIS_PROMPT",
    "REVISION_SYSTEM_PROMPT",
]
