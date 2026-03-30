"""
Scout Agent — discovers candidate properties and gathers market context.

LangGraph node signature: (state: AgentState) -> dict
Returns partial state update with: properties, market_context
"""

from state import AgentState
from tools.rera_scraper import search_rera_projects
from tools.market_data import get_market_overview, get_locality_comparison
from tools.news_engine import get_real_estate_news, get_regulatory_news


def scout_agent(state: AgentState) -> dict:
    location = state["location"]
    property_type = state["property_type"]
    budget_max_inr = state["budget_max_inr"]

    print(f"[Scout] Searching RERA projects in {location} for {property_type} under ₹{budget_max_inr/1e5:.0f}L...")

    # 1. Find RERA-registered projects
    properties = search_rera_projects(location, property_type, budget_max_inr)

    # 2. Gather market context
    market_overview = get_market_overview(location, property_type)
    locality_data = get_locality_comparison(location)
    news = get_real_estate_news(location)
    regulatory_news = get_regulatory_news(location)

    market_context = {
        "overview": market_overview,
        "locality_comparison": locality_data,
        "general_news": news,
        "regulatory_news": regulatory_news,
    }

    print(f"[Scout] Found {len(properties)} candidate properties.")

    return {
        "properties": properties,
        "market_context": market_context,
    }
