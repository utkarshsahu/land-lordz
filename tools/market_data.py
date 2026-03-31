"""
Fetches real estate market research (prices, locality insights, home loan rate)
for Indian cities using a single LLM call.
"""

import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from tools.coerce import to_float, to_list, strip_markdown_fences

log = logging.getLogger(__name__)
_llm = None
_SOURCES = (
    "Economic Times Real Estate, 99acres, Knight Frank India, Anarock, "
    "Magicbricks, Housing.com, JLL India, PropTiger, NoBroker"
)


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _llm


def get_market_research(location: str, property_type: str) -> dict:
    """
    Single LLM call that returns:
      - home_loan_rate_pct: current prevailing floating rate (% p.a.)
      - market_overview: 4 insights on prices, trends, yield, timing
      - locality_insights: top 5 micro-markets ranked by investment potential

    Each insight item has: title, snippet, link.
    """
    prompt = f"""You are an Indian real estate market expert. For {property_type} residential
properties in {location}, India, provide the following in a single JSON response:

1. home_loan_rate_pct — the current prevailing floating home loan rate (% p.a.) for
   salaried borrowers at SBI / HDFC / ICICI. Just a number, e.g. 8.75.

2. market_overview — exactly 4 insights covering:
   - Current price range (₹/sqft and ticket size in Lakhs)
   - Price trend over the past 1–2 years
   - Key demand drivers and rental yields
   - Buyer vs seller market signal

3. locality_insights — top 5 micro-markets in {location} ranked by investment potential,
   each with why it's attractive, typical ₹/sqft, and expected annual appreciation %.

Each item in market_overview and locality_insights must have:
  "title": short heading
  "snippet": 2–3 sentences with concrete data (₹/sqft, % figures, specific localities)
  "source": name of a well-known Indian real estate publication or research firm
             from this list: {_SOURCES}

Respond with ONLY valid JSON matching this schema (no markdown):
{{
  "home_loan_rate_pct": <number>,
  "market_overview": [
    {{"title": "...", "snippet": "...", "source": "..."}},
    ... 4 items
  ],
  "locality_insights": [
    {{"title": "<locality name>", "snippet": "...", "source": "..."}},
    ... 5 items
  ]
}}"""

    try:
        response = _get_llm().invoke([HumanMessage(content=prompt)])
        data = json.loads(strip_markdown_fences(response.content))

        # Coerce and validate all fields
        rate = to_float(data.get("home_loan_rate_pct"), 8.75)
        if not (6.0 <= rate <= 15.0):
            log.warning("[MarketData] Rate %.2f outside plausible range, using 8.75%%", rate)
            rate = 8.75
        data["home_loan_rate_pct"] = rate
        data["market_overview"] = to_list(data.get("market_overview"))
        data["locality_insights"] = to_list(data.get("locality_insights"))
        log.info("[MarketData] Research complete. home_loan_rate=%.2f%% overview=%d locality=%d",
                 rate, len(data["market_overview"]), len(data["locality_insights"]))
        return data

    except json.JSONDecodeError as e:
        log.error("[MarketData] JSON parse failed: %s\nRaw response:\n%s",
                  e, locals().get("response", {}).content if hasattr(locals().get("response", None), "content") else "N/A")
        return {
            "home_loan_rate_pct": 8.75,
            "market_overview": [{"title": "Data unavailable", "snippet": f"Could not retrieve market data for {location}.", "link": ""}],
            "locality_insights": [{"title": "Data unavailable", "snippet": f"Could not retrieve locality data for {location}.", "link": ""}],
        }
    except (AttributeError, ValueError, KeyError) as e:
        log.error("[MarketData] Research failed (%s: %s), returning defaults.", type(e).__name__, e)
        return {
            "home_loan_rate_pct": 8.75,
            "market_overview": [{"title": "Data unavailable", "snippet": f"Could not retrieve market data for {location}.", "link": ""}],
            "locality_insights": [{"title": "Data unavailable", "snippet": f"Could not retrieve locality data for {location}.", "link": ""}],
        }
