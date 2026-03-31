"""
Scout Agent — discovers candidate properties and gathers market context.

LangGraph node signature: (state: AgentState) -> dict
Returns partial state update with: properties, market_context
"""

import logging
import traceback
from state import AgentState
from tools.rera_scraper import search_rera_projects
from tools.market_data import get_market_research
from tools.news_engine import get_market_news

log = logging.getLogger(__name__)


def scout_agent(state: AgentState) -> dict:
    location = state["location"]
    property_type = state["property_type"]
    budget_max_inr = state["budget_max_inr"]

    log.info("[Scout] Starting. location=%r type=%r budget=₹%.0fL",
             location, property_type, budget_max_inr / 1e5)

    try:
        properties = search_rera_projects(location, property_type, budget_max_inr)
        log.info("[Scout] RERA search returned %d properties.", len(properties))
        for i, p in enumerate(properties):
            log.debug("[Scout] Property %d: %r | price_inr=%s | rera_id=%s",
                      i, p.get("name"), p.get("price_inr"), p.get("rera_id"))
    except Exception:
        log.error("[Scout] RERA search failed:\n%s", traceback.format_exc())
        properties = []

    try:
        research = get_market_research(location, property_type)
        log.info("[Scout] Market research complete. home_loan_rate=%.2f%%", research.get("home_loan_rate_pct", 0))
        log.debug("[Scout] market_overview items: %d | locality_insights: %d",
                  len(research.get("market_overview", [])),
                  len(research.get("locality_insights", [])))
    except Exception:
        log.error("[Scout] Market research failed:\n%s", traceback.format_exc())
        research = {"home_loan_rate_pct": 8.75, "market_overview": [], "locality_insights": []}

    try:
        news = get_market_news(location)
        log.info("[Scout] News fetched. general=%d | regulatory=%d",
                 len(news.get("general_news", [])),
                 len(news.get("regulatory_news", [])))
    except Exception:
        log.error("[Scout] News fetch failed:\n%s", traceback.format_exc())
        news = {"general_news": [], "regulatory_news": []}

    market_context = {
        "home_loan_rate_pct": research["home_loan_rate_pct"],
        "market_overview": research["market_overview"],
        "locality_insights": research["locality_insights"],
        "general_news": news["general_news"],
        "regulatory_news": news["regulatory_news"],
    }

    log.info("[Scout] Done. %d properties, home_loan_rate=%.2f%%",
             len(properties), research["home_loan_rate_pct"])
    return {"properties": properties, "market_context": market_context}
