"""Business-Specific Insight Generation Engine.

Synthesizes validated financial facts and management commentary into a structured
BusinessInsights object:
- Growth drivers (segment & top-line expansions)
- Profitability trends (margins, operating profit, PAT)
- Balance-sheet & capital strength (deposits, advances, CET1, net worth)
- Risk factors & asset quality (NPAs, provisions, cost pressure)
- Operational trends (branches, users, orders, stores)
- Business-specific KPIs
- Management commentary & guidance
- Data gaps (expected domain metrics not disclosed in source)
"""
from __future__ import annotations
from typing import Any
from ..core.contracts import BusinessContext, BusinessInsights, CanonicalFinancialFact, ManagementGuidance


def generate_business_insights(
    facts: list[CanonicalFinancialFact],
    guidance: list[ManagementGuidance],
    context: BusinessContext
) -> BusinessInsights:
    """Produces structured domain-specific insights from canonical facts and guidance."""
    growth_drivers: list[dict[str, Any]] = []
    profitability_trends: list[dict[str, Any]] = []
    operational_trends: list[dict[str, Any]] = []
    risk_factors: list[dict[str, Any]] = []
    balance_sheet_strength: list[dict[str, Any]] = []
    business_specific_trends: list[dict[str, Any]] = []
    management_commentary: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []

    # Map facts by metric name
    facts_by_metric: dict[str, list[CanonicalFinancialFact]] = {}
    for f in facts:
        facts_by_metric.setdefault(f.metric_name, []).append(f)

    # 1. Growth Drivers
    for f in facts:
        if f.growth is not None and f.growth > 0 and f.relevance_score >= 0.7:
            growth_drivers.append({
                "metric": f.metric_name,
                "period": f.period,
                "value": f"{f.value} {f.unit}",
                "growth_pct": f"{f.growth}% {f.growth_type or 'YoY'}",
                "insight": f"{f.metric_name} expanded by {f.growth}% ({f.period}: {f.value} {f.unit})",
                "source_page": f.source_page
            })
        elif f.category == "growth" and f.relevance_score >= 0.75:
            growth_drivers.append({
                "metric": f.metric_name,
                "period": f.period,
                "value": f"{f.value} {f.unit}",
                "growth_pct": f"{f.growth}%" if f.growth else "Stated",
                "insight": f"{f.metric_name} reported at {f.value} {f.unit} for {f.period}",
                "source_page": f.source_page
            })

    # 2. Profitability Trends
    prof_metrics = ("Profit After Tax", "Net Interest Income", "Core Operating Profit",
                    "Net Interest Margin", "Revenue from Operations", "Adjusted EBITDA",
                    "EBITDA", "EBITDA Margin", "Cost to Income Ratio", "Return on Assets")
    for m in prof_metrics:
        if m in facts_by_metric:
            for f in facts_by_metric[m][:2]:
                detail = f"{f.metric_name}: {f.value} {f.unit} in {f.period}"
                if f.growth is not None:
                    detail += f" ({'+' if f.growth > 0 else ''}{f.growth}% YoY)"
                profitability_trends.append({
                    "metric": f.metric_name,
                    "value": f"{f.value} {f.unit}",
                    "period": f.period,
                    "trend": "upward" if (f.growth and f.growth > 0) else "stable",
                    "insight": detail,
                    "source_page": f.source_page
                })

    # 3. Balance Sheet & Capital Position
    bs_metrics = ("Total Deposits", "Total Advances", "CASA Ratio", "CET1 Ratio",
                  "Capital Adequacy Ratio", "Net Worth", "Assets Under Management")
    for m in bs_metrics:
        if m in facts_by_metric:
            for f in facts_by_metric[m][:2]:
                balance_sheet_strength.append({
                    "metric": f.metric_name,
                    "value": f"{f.value} {f.unit}",
                    "period": f.period,
                    "insight": f"{f.metric_name} stood at {f.value} {f.unit} ({f.period})",
                    "source_page": f.source_page
                })

    # 4. Risk Factors & Asset Quality
    risk_metrics = ("Gross NPA Ratio", "Net NPA Ratio", "Provisions", "Gross NPA",
                    "Net NPA", "Provision Coverage Ratio", "Combined Ratio")
    for m in risk_metrics:
        if m in facts_by_metric:
            for f in facts_by_metric[m][:2]:
                risk_factors.append({
                    "metric": f.metric_name,
                    "value": f"{f.value} {f.unit}",
                    "period": f.period,
                    "insight": f"{f.metric_name} reported at {f.value} {f.unit} ({f.period})",
                    "source_page": f.source_page
                })

    # 5. Operational Trends
    op_metrics = ("Total Orders", "Monthly Transacting Users", "Dark Stores",
                  "Retail Loans", "Business Banking Loans", "Average Order Value")
    for m in op_metrics:
        if m in facts_by_metric:
            for f in facts_by_metric[m][:2]:
                operational_trends.append({
                    "metric": f.metric_name,
                    "value": f"{f.value} {f.unit}",
                    "period": f.period,
                    "insight": f"{f.metric_name} reached {f.value} {f.unit} ({f.period})",
                    "source_page": f.source_page
                })

    # 6. Sector-Specific Portfolio Trends
    if context.business_model == "banking":
        # Bank-specific loan mix & asset quality summary
        advances = facts_by_metric.get("Total Advances", [])
        deposits = facts_by_metric.get("Total Deposits", [])
        if advances and deposits:
            business_specific_trends.append({
                "topic": "Credit & Deposit Franchise",
                "insight": f"Advances stood at {advances[0].value} {advances[0].unit} alongside total deposits of {deposits[0].value} {deposits[0].unit}.",
                "source_page": advances[0].source_page
            })
    elif context.business_model == "consumer_internet":
        gov = facts_by_metric.get("Gross Order Value", [])
        nov = facts_by_metric.get("Net Order Value", [])
        if gov or nov:
            lead = nov[0] if nov else gov[0]
            business_specific_trends.append({
                "topic": "Order Value Growth",
                "insight": f"{lead.metric_name} scaled to {lead.value} {lead.unit} ({lead.period}).",
                "source_page": lead.source_page
            })

    # 7. Management Commentary & Guidance
    for g in guidance[:6]:
        management_commentary.append({
            "statement": g.statement,
            "target_period": g.target_period or "Future",
            "source_page": g.source_page
        })

    # 8. Data Gaps (Identifies expected primary metrics missing in source)
    present_metric_names = set(facts_by_metric.keys())
    for exp in context.primary_metrics:
        if exp not in present_metric_names and not any(exp.lower() in p.lower() for p in present_metric_names):
            data_gaps.append({
                "metric": exp,
                "status": "not_disclosed",
                "note": f"{exp} is a standard {context.sector} KPI but not explicitly tabulated in this source."
            })

    return BusinessInsights(
        growth_drivers=growth_drivers[:8],
        profitability_trends=profitability_trends[:8],
        operational_trends=operational_trends[:6],
        risk_factors=risk_factors[:6],
        balance_sheet_strength=balance_sheet_strength[:6],
        business_specific_trends=business_specific_trends[:4],
        management_commentary=management_commentary[:6],
        data_gaps=data_gaps[:6]
    )
