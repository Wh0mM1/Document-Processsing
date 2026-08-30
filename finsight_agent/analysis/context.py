"""Document Understanding & Business Context Stage.

Analyzes document metadata, initial pages, and structure to determine:
- Company name
- Sector / industry
- Document type (research report, investor presentation, earnings release, etc.)
- Reporting period & date
- Business model / domain (banking, consumer internet, insurance, etc.)
- Primary financial metrics relevant to this specific domain
- Presence of analyst metadata (rating, target, estimates)
"""
from __future__ import annotations
import re
from typing import Any
from ..core.contracts import BusinessContext


# Sector concept profiles
SECTOR_METRIC_PROFILES: dict[str, list[str]] = {
    "banking": [
        "PAT", "NII", "NIM", "Core Operating Profit", "PBT excl Treasury",
        "Deposits", "Advances", "CASA Ratio", "GNPA Ratio", "NNPA Ratio",
        "Provision Coverage Ratio", "Provisions", "CET1 Ratio", "Capital Adequacy Ratio",
        "Cost-to-Income Ratio", "Return on Assets"
    ],
    "consumer_internet": [
        "Revenue", "Gross Order Value (GOV)", "Net Order Value (NOV)",
        "Adjusted EBITDA", "EBITDA", "EBITDA Margin", "PAT", "Contribution Margin",
        "Orders", "Monthly Transacting Customers", "Dark Stores", "Average Order Value"
    ],
    "insurance": [
        "Gross Written Premium (GWP)", "Annualized Premium Equivalent (APE)",
        "Value of New Business (VNB)", "VNB Margin", "Solvency Ratio",
        "Combined Ratio", "Claims Ratio", "Persistency Ratio", "Assets Under Management"
    ],
    "nbfc": [
        "Assets Under Management (AUM)", "Disbursements", "NII", "NIM",
        "PAT", "GNPA", "NNPA", "Provisioning", "Cost of Borrowing", "CRAR"
    ],
    "technology": [
        "Revenue", "Constant Currency Growth", "EBIT", "EBIT Margin",
        "PAT", "TCV Deal Wins", "Attrition Rate", "Utilization", "Free Cash Flow"
    ],
    "manufacturing": [
        "Revenue", "EBITDA", "EBITDA Margin", "Operating Profit", "PAT",
        "Sales Volume", "Capacity Utilization", "Realization", "Raw Material Cost", "Capex"
    ],
    "general": [
        "Revenue", "Operating Profit", "EBITDA", "EBITDA Margin", "PAT",
        "Net Profit Margin", "Cash Flow from Operations", "Debt-to-Equity", "EPS"
    ]
}


def analyze_document_context(pages: list[dict[str, Any]], manifest: dict[str, Any] | None = None) -> BusinessContext:
    """Classifies document context, business domain, and dynamically selects relevant metrics."""
    # Consolidate first 6 pages of text
    first_pages = pages[:6]
    text_corpus = "\n".join([p.get("text", "") for p in first_pages])
    full_text_sample = "\n".join([p.get("text", "") for p in pages[:15]])
    last_page_text = pages[-1].get("text", "") if pages else ""

    # 1. Company Name Detection
    company = "Unknown Company"
    if "ICICI Bank" in full_text_sample or "ICICI Bank" in text_corpus:
        company = "ICICI Bank Limited"
    elif "Eternal Limited" in text_corpus or "Zomato Limited" in text_corpus or "Eternal" in text_corpus:
        company = "Eternal Limited"
    else:
        # Generic heuristic: check first 1-2 pages for company titles
        match = re.search(r"([A-Z][A-Za-z0-9\s&.,-]{2,40}(?:Limited|Ltd|Bank|Corporation|Inc|Corp))\b", text_corpus)
        if match:
            company = match.group(1).strip()
        else:
            # Check title of page 1 or 2
            for p in first_pages[:2]:
                title = p.get("title")
                if title and len(title) > 3 and not title.startswith("Page") and not re.match(r"^\d+$", title):
                    company = title.strip()
                    break

    # 2. Sector & Business Model Detection
    score_banking = len(re.findall(r"\b(bank|nii|net interest income|advances|deposits|casa|npa|gnpa|nnpa|cet1|capital adequacy|basel iii|credit cost|nim)\b", text_corpus, re.I))
    score_consumer = len(re.findall(r"\b(food delivery|quick commerce|blinkit|hyperpure|zomato|dark stores|gov|nov|gross order value|net order value|orders|dining-out)\b", text_corpus, re.I))
    score_insurance = len(re.findall(r"\b(premium|gwp|vnb|ape|solvency|persistency|claims ratio|underwriting|actuarial)\b", text_corpus, re.I))
    score_tech = len(re.findall(r"\b(it services|digital revenue|constant currency|tcv|deal wins|attrition|headcount|cloud services)\b", text_corpus, re.I))

    if score_banking >= max(score_consumer, score_insurance, score_tech, 3):
        sector = "Banking & Financial Services"
        business_model = "banking"
    elif score_consumer >= max(score_banking, score_insurance, score_tech, 3):
        sector = "Internet & Consumer Technology"
        business_model = "consumer_internet"
    elif score_insurance >= max(score_banking, score_consumer, score_tech, 3):
        sector = "Insurance"
        business_model = "insurance"
    elif score_tech >= max(score_banking, score_consumer, score_insurance, 3):
        sector = "Technology & IT Services"
        business_model = "technology"
    else:
        sector = "Diversified / General Business"
        business_model = "general"

    # 3. Document Type Detection
    has_research_signatures = bool(
        re.search(r"recommendation summary|rating criteria|geojit|target price|target\s*:\s*rs|analyst certification|old estimates|new estimates", text_corpus + "\n" + last_page_text, re.I)
    )
    has_investor_pres_signatures = bool(
        re.search(r"investor presentation|performance review|bse limited.*listing department|safe harbor|performance highlights|quarterly results presentation", text_corpus, re.I)
    )
    has_annual_report_signatures = bool(
        re.search(r"annual report|integrated report|board's report|notice of annual general meeting", text_corpus, re.I)
    )
    has_press_release_signatures = bool(
        re.search(r"press release|media release|financial results for the quarter ended", text_corpus, re.I)
    )

    if has_research_signatures:
        document_type = "equity_research_report"
    elif has_investor_pres_signatures:
        document_type = "investor_presentation"
    elif has_annual_report_signatures:
        document_type = "annual_report"
    elif has_press_release_signatures:
        document_type = "earnings_release"
    else:
        document_type = "financial_statement"

    # 4. Reporting Period & Document Date Detection
    period = "Current Period"
    period_matches = re.findall(r"\b(Q[1-4][-\s]?(?:FY)?\d{2,4}|H[12][-\s]?(?:FY)?\d{2,4}|FY\d{2,4})\b", text_corpus, re.I)
    if period_matches:
        # Pick the most frequently mentioned or prominent period in first 3 pages
        freq: dict[str, int] = {}
        for m in period_matches:
            norm = m.upper().replace(" ", "").replace("-", "")
            freq[norm] = freq.get(norm, 0) + 1
        period = max(freq, key=freq.get)

    date_match = re.search(r"\b(\d{1,2}[-/](?:[A-Za-z]{3}|\d{1,2})[-/]\d{2,4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b", text_corpus, re.I)
    document_date = date_match.group(1).strip() if date_match else None

    # 5. Currency and Base Units Detection
    reporting_currency_unit = "₹ billion"
    if "rs.cr" in text_corpus.lower() or "rs cr" in text_corpus.lower() or "crore" in text_corpus.lower():
        reporting_currency_unit = "₹ crore"
    elif "billion" in text_corpus.lower() or "₹ billion" in text_corpus.lower() or "bn" in text_corpus.lower():
        reporting_currency_unit = "₹ billion"
    elif "usd million" in text_corpus.lower() or "$ million" in text_corpus.lower():
        reporting_currency_unit = "USD million"

    # 6. Broker / Analyst Metadata Check
    has_target_and_rating = bool(has_research_signatures and re.search(r"\b(target\s*(?:price|:)|rating\s*:|BUY|HOLD|SELL|ACCUMULATE|REDUCE)\b", text_corpus + "\n" + last_page_text, re.I))
    has_analyst_estimates = bool(has_research_signatures or re.search(r"\b(FY\d{2}E|new estimates|old estimates)\b", text_corpus, re.I))

    # 7. Select Primary Metrics
    primary_metrics = SECTOR_METRIC_PROFILES.get(business_model, SECTOR_METRIC_PROFILES["general"])

    summary = (
        f"{company} operates in {sector} ({business_model}). "
        f"The source document is a {document_type.replace('_', ' ').title()} for period {period} "
        f"({f'dated {document_date}' if document_date else 'undated'}). "
        f"Primary analysis metrics: {', '.join(primary_metrics[:6])}."
    )

    return BusinessContext(
        company=company,
        sector=sector,
        document_type=document_type,
        period=period,
        document_date=document_date,
        business_model=business_model,
        primary_metrics=primary_metrics,
        reporting_currency_unit=reporting_currency_unit,
        has_analyst_estimates=has_analyst_estimates,
        has_target_and_rating=has_target_and_rating,
        context_summary=summary
    )
