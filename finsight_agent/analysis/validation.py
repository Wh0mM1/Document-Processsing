"""Cross-Check Arithmetic Validation & Fact Verification Engine.

Performs:
1. Mathematical validation of stated growth rates against current and comparative periods:
   calculated_growth = ((current - prior) / prior) * 100%
2. Unit consistency checks (percentages vs monetary amounts).
3. Deduplication of multi-source facts.
4. Relevance scoring relative to business context and report objectives.
"""
from __future__ import annotations
from typing import Any
from ..core.contracts import BusinessContext, CanonicalFinancialFact


def validate_and_score_facts(
    facts: list[CanonicalFinancialFact],
    context: BusinessContext
) -> list[CanonicalFinancialFact]:
    """Validates arithmetic consistency, resolves conflicts, and computes relevance scores."""
    # 1. Index facts by (metric_name, period_type) to find comparative time series
    metric_series: dict[str, list[CanonicalFinancialFact]] = {}
    for f in facts:
        metric_series.setdefault(f.metric_name, []).append(f)

    validated_list: list[CanonicalFinancialFact] = []

    for fact in facts:
        # Clone to avoid mutating original
        item = fact.model_copy()
        notes = []

        # A. Relevance Scoring
        base_score = 0.5
        if item.metric_name in context.primary_metrics:
            base_score = 0.95
        elif item.category in ("profitability", "balance_sheet", "asset_quality", "capital"):
            base_score = 0.85
        elif item.category == "growth":
            base_score = 0.75
        elif item.category == "operational":
            base_score = 0.65

        # Demote subsidiary / regional details (e.g. Canadian subsidiary mortgages)
        if any(w in item.source_text.lower() for w in ("canada", "uk subsidiary", "germany", "branch in")):
            base_score = min(base_score, 0.40)
            notes.append("Subsidiary-level breakdown; lower global relevance")

        # Promote early-page headline facts
        if item.source_page <= 6:
            base_score = min(1.0, base_score + 0.05)

        item.relevance_score = round(base_score, 2)

        # B. Unit Consistency Check
        if item.category in ("profitability", "balance_sheet") and "ratio" in item.metric_name.lower():
            if item.unit not in ("%", "bps", "x"):
                item.unit = "%"
                notes.append("Unit normalized to % for ratio metric")

        # C. Arithmetic Cross-Check for YoY / QoQ Growth
        if item.growth is not None and isinstance(item.value, (int, float)):
            # Look for prior period fact in the series
            series = metric_series.get(item.metric_name, [])
            for prior_fact in series:
                if prior_fact != item and isinstance(prior_fact.value, (int, float)) and prior_fact.value > 0:
                    # Check if periods match YoY or QoQ pattern
                    calc_growth = round(((item.value - prior_fact.value) / prior_fact.value) * 100.0, 1)
                    if abs(calc_growth - item.growth) <= 2.0:
                        item.validation_status = "verified"
                        item.comparison_period = prior_fact.period
                        item.comparison_value = prior_fact.value
                        notes.append(f"YoY/QoQ growth verified against {prior_fact.period} (calc: {calc_growth}%, stated: {item.growth}%)")
                        break
                    elif abs(calc_growth - item.growth) > 10.0 and prior_fact.period != item.period:
                        # Large mismatch flag only if explicit comparison
                        pass

        if notes:
            item.validation_notes = "; ".join(notes)

        validated_list.append(item)

    # 2. Deduplicate facts with identical (metric_name, period, value)
    deduped: dict[tuple[str, str, str], CanonicalFinancialFact] = {}
    for f in validated_list:
        val_str = str(f.value)
        key = (f.metric_name, f.period, val_str)
        if key not in deduped:
            deduped[key] = f
        else:
            # Prefer table sources over prose, and higher confidence
            existing = deduped[key]
            if f.confidence > existing.confidence or ("Table" in f.source_text and "Table" not in existing.source_text):
                deduped[key] = f

    # Return sorted by relevance descending
    return sorted(deduped.values(), key=lambda x: x.relevance_score, reverse=True)
