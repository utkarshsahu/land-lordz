"""
Strategist Agent — synthesizes all analysis into a final investment strategy report.

LangGraph node signature: (state: AgentState) -> dict
Returns partial state update with: strategy_report
"""

import json
import os
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from state import AgentState

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
        fa for fa in financial_analyses if fa["property_name"] in shortlisted
    ]

    # Summarise market snippets to avoid token bloat
    market_snippets = [
        s.get("snippet", "")
        for s in market_context.get("overview", {}).get("market_snippets", [])
    ][:3]
    news_headlines = [
        n.get("title", "") for n in market_context.get("general_news", [])
    ][:4]

    context = {
        "query": query,
        "location": location,
        "property_type": property_type,
        "budget_inr": budget_max_inr,
        "shortlisted_properties": shortlisted_analyses,
        "risk_summary": audit_report.get("risk_summary"),
        "all_audits": audit_report.get("property_audits"),
        "market_context_snippets": market_snippets,
        "recent_news": news_headlines,
    }

    system_prompt = """You are a senior Indian real estate investment strategist.
You produce clear, actionable, and data-backed investment reports in Markdown.
Always include: executive summary, market overview, property rankings with rationale,
risk assessment, and a clear recommendation. Use ₹ (INR) for all monetary values.
Format all numbers with Indian number system (lakhs, crores). Today's date: """ + datetime.now().strftime("%B %d, %Y")

    human_prompt = f"""Analyse the following data and produce a comprehensive Markdown investment report.

DATA:
{json.dumps(context, indent=2, default=str)}

Structure the report with these sections:
1. ## Executive Summary
2. ## User Query & Parameters
3. ## Market Overview — {location}
4. ## Shortlisted Properties (ranked best to worst)
   - For each: name, RERA status, key financials table, pros/cons
5. ## Risk Assessment
6. ## Investment Recommendation
7. ## Next Steps & Due Diligence Checklist

Use tables for financial comparisons. Be specific with numbers."""

    llm = _get_llm()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ])

    strategy_report = response.content
    print("[Strategist] Report generated.")
    return {"strategy_report": strategy_report}
