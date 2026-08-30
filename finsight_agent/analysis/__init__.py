"""Document analysis sub-package: context detection, fact extraction, insights, charts."""
from .context import analyze_document_context
from .extraction import extract_context_aware_facts
from .validation import validate_and_score_facts
from .insights import generate_business_insights
from .charts import plan_contextual_charts

__all__ = [
    "analyze_document_context",
    "extract_context_aware_facts",
    "validate_and_score_facts",
    "generate_business_insights",
    "plan_contextual_charts",
]
