"""Context-Aware Chart Planner.

Dynamically selects the most meaningful financial charts based on business context
and available time-series data:
- Banking: PAT Trend, NII Trend, Total Advances & Deposits Trend, Asset Quality (NPA) Trend
- Consumer/Tech: Revenue Trend, EBITDA Trend, Order Value (GOV/NOV) Trend, PAT Trend
- General/Manufacturing: Revenue Trend, EBITDA Trend, Net Profit Trend
"""
from __future__ import annotations
from typing import Any
from ..core.contracts import BusinessContext, CanonicalFinancialFact, ChartPoint, ChartSpec, Citation


def plan_contextual_charts(
    facts: list[CanonicalFinancialFact],
    context: BusinessContext
) -> list[ChartSpec]:
    """Evaluates available time-series facts and constructs 2-4 domain-relevant chart specifications."""
    # Group facts by metric_name
    series_map: dict[str, list[CanonicalFinancialFact]] = {}
    for f in facts:
        if isinstance(f.value, (int, float)) and f.value is not None:
            series_map.setdefault(f.metric_name, []).append(f)

    # Sort each series chronologically by period
    for metric_name, items in series_map.items():
        # Keep unique periods per metric
        period_seen: set[str] = set()
        clean_items = []
        for it in items:
            if it.period not in period_seen:
                period_seen.add(it.period)
                clean_items.append(it)
        series_map[metric_name] = clean_items

    selected_charts: list[ChartSpec] = []

    # Banking Priority Visualizations
    if context.business_model == "banking":
        # 1. PAT Trend
        if "Profit After Tax" in series_map and len(series_map["Profit After Tax"]) >= 2:
            pts = [ChartPoint(
                period=f.period,
                value=float(f.value),
                unit=f.unit,
                citations=[Citation(page=f.source_page, excerpt=f.source_text[:100])]
            ) for f in series_map["Profit After Tax"]]
            selected_charts.append(ChartSpec(
                title=f"{context.company} - Profit After Tax Trend",
                metric="Profit After Tax",
                category="profitability",
                chart_type="bar",
                rationale="Core bottom-line profitability indicator for banking franchise.",
                points=pts[-6:]
            ))

        # 2. NII Trend
        if "Net Interest Income" in series_map and len(series_map["Net Interest Income"]) >= 2:
            pts = [ChartPoint(
                period=f.period,
                value=float(f.value),
                unit=f.unit,
                citations=[Citation(page=f.source_page, excerpt=f.source_text[:100])]
            ) for f in series_map["Net Interest Income"]]
            selected_charts.append(ChartSpec(
                title=f"{context.company} - Net Interest Income (NII) Trend",
                metric="Net Interest Income",
                category="profitability",
                chart_type="bar",
                rationale="Primary interest earning driver of the bank's core balance sheet.",
                points=pts[-6:]
            ))

        # 3. Advances Trend
        if "Total Advances" in series_map and len(series_map["Total Advances"]) >= 2:
            pts = [ChartPoint(
                period=f.period,
                value=float(f.value),
                unit=f.unit,
                citations=[Citation(page=f.source_page, excerpt=f.source_text[:100])]
            ) for f in series_map["Total Advances"]]
            selected_charts.append(ChartSpec(
                title=f"{context.company} - Loan Portfolio / Advances Trend",
                metric="Total Advances",
                category="balance_sheet",
                chart_type="line",
                rationale="Demonstrates overall credit expansion across domestic retail and corporate loans.",
                points=pts[-6:]
            ))

        # 4. Asset Quality (GNPA / NNPA)
        if "Net NPA Ratio" in series_map and len(series_map["Net NPA Ratio"]) >= 2:
            pts = [ChartPoint(
                period=f.period,
                value=float(f.value),
                unit=f.unit,
                citations=[Citation(page=f.source_page, excerpt=f.source_text[:100])]
            ) for f in series_map["Net NPA Ratio"]]
            selected_charts.append(ChartSpec(
                title=f"{context.company} - Net NPA Ratio Trend (%)",
                metric="Net NPA Ratio",
                category="asset_quality",
                chart_type="line",
                rationale="Tracks asset quality improvements and credit risk trajectory.",
                points=pts[-6:]
            ))

    # Consumer / Internet Priority Visualizations
    elif context.business_model == "consumer_internet":
        # 1. Revenue from Operations
        if "Revenue from Operations" in series_map and len(series_map["Revenue from Operations"]) >= 2:
            pts = [ChartPoint(
                period=f.period,
                value=float(f.value),
                unit=f.unit,
                citations=[Citation(page=f.source_page, excerpt=f.source_text[:100])]
            ) for f in series_map["Revenue from Operations"]]
            selected_charts.append(ChartSpec(
                title=f"{context.company} - Revenue from Operations Trend",
                metric="Revenue from Operations",
                category="growth",
                chart_type="bar",
                rationale="Top-line monetization trajectory across B2C food delivery and quick commerce.",
                points=pts[-6:]
            ))

        # 2. EBITDA / Adjusted EBITDA
        lead_ebitda = "Adjusted EBITDA" if "Adjusted EBITDA" in series_map else "EBITDA"
        if lead_ebitda in series_map and len(series_map[lead_ebitda]) >= 2:
            pts = [ChartPoint(
                period=f.period,
                value=float(f.value),
                unit=f.unit,
                citations=[Citation(page=f.source_page, excerpt=f.source_text[:100])]
            ) for f in series_map[lead_ebitda]]
            selected_charts.append(ChartSpec(
                title=f"{context.company} - {lead_ebitda} Trend",
                metric=lead_ebitda,
                category="profitability",
                chart_type="bar",
                rationale="Key operational efficiency and contribution margin progression indicator.",
                points=pts[-6:]
            ))

        # 3. PAT Trend
        if "Profit After Tax" in series_map and len(series_map["Profit After Tax"]) >= 2:
            pts = [ChartPoint(
                period=f.period,
                value=float(f.value),
                unit=f.unit,
                citations=[Citation(page=f.source_page, excerpt=f.source_text[:100])]
            ) for f in series_map["Profit After Tax"]]
            selected_charts.append(ChartSpec(
                title=f"{context.company} - Net Profit / PAT Trend",
                metric="Profit After Tax",
                category="profitability",
                chart_type="bar",
                rationale="Bottom-line earnings trajectory.",
                points=pts[-6:]
            ))

    # General / Multi-Domain Fallback
    if not selected_charts:
        for metric_name in ("Revenue from Operations", "Profit After Tax", "EBITDA", "Total Deposits", "Total Advances"):
            if metric_name in series_map and len(series_map[metric_name]) >= 2:
                pts = [ChartPoint(
                    period=f.period,
                    value=float(f.value),
                    unit=f.unit,
                    citations=[Citation(page=f.source_page, excerpt=f.source_text[:100])]
                ) for f in series_map[metric_name]]
                selected_charts.append(ChartSpec(
                    title=f"{context.company} - {metric_name} Trend",
                    metric=metric_name,
                    category="trend",
                    chart_type="bar",
                    rationale="Primary reported financial series.",
                    points=pts[-6:]
                ))
                if len(selected_charts) >= 3:
                    break

    return selected_charts
