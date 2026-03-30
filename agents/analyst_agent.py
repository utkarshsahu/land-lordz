"""
Analyst Agent — enriches properties with financial metrics and LLM-generated insights.

LangGraph node signature: (state: AgentState) -> dict
Returns partial state update with: financial_analyses
"""

import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from state import AgentState
from tools.finance_utils import full_financial_profile

_llm = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _llm


def _estimate_missing_financials(property: dict, location: str, budget_max_inr: float) -> dict:
    """
    Use LLM to estimate price_inr and monthly_rent_inr when not available
    from the scraped data, based on location and property type context.
    """
    llm = _get_llm()
    prompt = f"""You are an Indian real estate expert. Given this property listing snippet, estimate:
1. Approximate price in INR (as a number)
2. Approximate monthly rent in INR (as a number)
3. Approximate area in sqft (as a number)

Property: {property.get('name', '')}
Description: {property.get('description', '')}
Location: {location}
Type: {property.get('property_type', '')}
Budget ceiling: ₹{budget_max_inr/1e5:.0f} Lakhs

Respond ONLY with valid JSON: {{"price_inr": number, "monthly_rent_inr": number, "area_sqft": number}}
Do not add any explanation."""

    response = llm.invoke([HumanMessage(content=prompt)])
    try:
        estimates = json.loads(response.content.strip())
        return estimates
    except (json.JSONDecodeError, AttributeError):
        # Safe fallback based on budget midpoint
        fallback_price = budget_max_inr * 0.85
        return {
            "price_inr": fallback_price,
            "monthly_rent_inr": fallback_price * 0.003,  # ~3.6% annual yield
            "area_sqft": 900,
        }


def analyst_agent(state: AgentState) -> dict:
    properties = state["properties"]
    location = state["location"]
    budget_max_inr = state["budget_max_inr"]

    print(f"[Analyst] Running financial analysis on {len(properties)} properties...")

    financial_analyses = []

    for prop in properties:
        # Fill in estimated financials if not scraped
        if not prop.get("price_inr"):
            estimates = _estimate_missing_financials(prop, location, budget_max_inr)
            prop.update(estimates)

        profile = full_financial_profile(prop)

        financial_analyses.append({
            "property_name": prop.get("name", "Unknown"),
            "location": prop.get("location", location),
            "rera_id": prop.get("rera_id"),
            "builder": prop.get("builder"),
            "source_url": prop.get("source_url"),
            "financials": profile,
            "raw_property": prop,
        })

    print(f"[Analyst] Financial profiles computed for {len(financial_analyses)} properties.")
    return {"financial_analyses": financial_analyses}
