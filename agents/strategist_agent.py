"""
Strategist Agent — synthesizes all analysis into a final investment strategy report.

LangGraph node signature: (state: AgentState) -> dict
Returns partial state update with: strategy_report
"""

import json
import logging
import os
import traceback
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from state import AgentState

log = logging.getLogger(__name__)
_llm = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    return _llm


def strategist_agent(state: AgentState) -> dict:
    query = state["query"]
    location = state["location"]
    property_type = state["property_type"]
    budget_max_inr = state["budget_max_inr"]
    financial_analyses = state["financial_analyses"]
    audit_report = state["audit_report"]
    market_context = state["market_context"]

    print("[Strategist] Generating investment strategy report...")

    # Build a compact context payload for the LLM
    shortlisted = audit_report.get("shortlisted", [])
    shortlisted_analyses = [
        fa for fa in financial_analyses if fa.get("property_name") in shortlisted
    ]

    context = {
        "query": query,
        "location": location,
        "property_type": property_type,
        "budget_inr": budget_max_inr,
        "home_loan_rate_pct": market_context.get("home_loan_rate_pct") or 8.75,
        "shortlisted_properties": shortlisted_analyses,
        "risk_summary": audit_report.get("risk_summary"),
        "all_audits": audit_report.get("property_audits"),
        "market_overview": market_context.get("market_overview", []),
        "locality_insights": market_context.get("locality_insights", []),
        "general_news": market_context.get("general_news", []),
        "regulatory_news": market_context.get("regulatory_news", []),
    }

    system_prompt = """You are a senior Indian real estate investment strategist.
You produce clear, actionable, and data-backed investment reports in Markdown.
Always include: executive summary, market overview, property rankings with rationale,
risk assessment, and a clear recommendation. Use ₹ (INR) for all monetary values.
Format all numbers with Indian number system (lakhs, crores).
When using a market insight, news item, or locality data point, cite the source inline by name only
(no hyperlinks), e.g. "Prices have risen 12% YoY (Knight Frank India)".
Do NOT generate or guess any URLs — the only hyperlink allowed per property is its listing URL.
Today's date: """ + datetime.now().strftime("%B %d, %Y")

    home_loan_rate_pct = context["home_loan_rate_pct"]
    human_prompt = f"""Analyse the following data and produce a comprehensive Markdown investment report.

DATA:
{json.dumps(context, indent=2, default=str)}

Structure the report with these sections:
1. ## Executive Summary
2. ## User Query & Parameters
3. ## Market Overview — {location}
4. ## Shortlisted Properties (ranked best to worst)
   - For each property include:
     - RERA ID, builder, and a link to the listing: [View Listing](source_url) — use the actual source_url from the data
     - A financials table with EXACTLY these rows (no others, no totals row):
       | Metric | Value |
       |--------|-------|
       | Purchase Price | ₹X,XX,XXX |
       | Carpet Area | XXX sq ft |
       | Price per sq ft | ₹X,XXX |
       | Expected Monthly Rent | ₹XX,XXX |
       | Rental Yield | X.X% |
       | Cap Rate | X.X% |
       | EMI ({home_loan_rate_pct}%, 20yr, 80% LTV) | ₹XX,XXX/month |
       | Stamp Duty | ₹X,XX,XXX |
       | Registration | ₹XX,XXX |
     - **Rent Basis**: include the rent_rationale from the data as a one-line note below the table
     - Pros and cons (bullet points)
5. ## Risk Assessment
6. ## Investment Recommendation
7. ## Next Steps & Due Diligence Checklist

Use Indian number formatting (lakhs/crores) in prose. Be specific with numbers.
Cite sources inline by name only (no URLs), e.g. "(Anarock)" or "(Knight Frank India)".
Use the "source" field from market_overview, locality_insights, general_news, and regulatory_news items.
The ONLY hyperlinks allowed are the listing URLs per property (source_url from the data)."""

    log.info("[Strategist] Sending context to LLM. shortlisted=%d | context_keys=%s",
             len(shortlisted_analyses), list(context.keys()))
    log.debug("[Strategist] Full context payload:\n%s", json.dumps(context, indent=2, default=str))

    try:
        llm = _get_llm()
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ])
        strategy_report = response.content
        log.info("[Strategist] Report generated. length=%d chars", len(strategy_report))
        log.debug("[Strategist] Report preview (first 300 chars):\n%s", strategy_report[:300])
    except Exception:
        log.error("[Strategist] LLM call failed:\n%s", traceback.format_exc())
        raise

    return {"strategy_report": strategy_report}
