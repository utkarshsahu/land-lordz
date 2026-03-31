"""
Generates real estate market news and regulatory context for Indian cities
using a single LLM call.
"""

import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from tools.geo_utils import resolve_city_state
from tools.coerce import to_list, strip_markdown_fences

log = logging.getLogger(__name__)
_llm = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
    return _llm


def get_market_news(location: str) -> dict:
    """
    Single LLM call that returns:
      - general_news: 5 key market dynamics / recent developments
      - regulatory_news: 4 RERA / compliance points buyers must know

    Each item has: title, snippet, source, link.
    Returns dict with keys "general_news" and "regulatory_news".
    """
    geo = resolve_city_state(location)
    state = geo["state"]
    rera_portal = geo["rera_portal"]

    prompt = f"""You are an Indian real estate analyst and compliance expert.
For {location} ({state}), provide both of the following in a single JSON response:

1. general_news — 5 key market dynamics or recent developments shaping residential
   property in {location}. Cover infrastructure, price movements, new supply, builder
   activity, demand shifts, NRI investment, or economic factors.

2. regulatory_news — 4 essential RERA / compliance points a buyer in {location} must know.
   Cover: registration requirements, builder compliance record, consumer protection
   provisions, completion certificate norms, or {state}-specific rules.

Each item must have:
  "title": short headline (< 10 words)
  "snippet": 2-sentence explanation with concrete data where possible
  "source": name of a well-known Indian publication or portal
    — for general_news use sources like: Economic Times, Anarock, JLL India, 99acres, Knight Frank India
    — for regulatory_news use sources like: {rera_portal}, RERA India, Livemint, Housing.com

Respond with ONLY valid JSON (no markdown):
{{
  "general_news": [
    {{"title": "...", "snippet": "...", "source": "..."}},
    ... 5 items
  ],
  "regulatory_news": [
    {{"title": "...", "snippet": "...", "source": "..."}},
    ... 4 items
  ]
}}"""

    try:
        response = _get_llm().invoke([HumanMessage(content=prompt)])
        raw = response.content
        data = json.loads(strip_markdown_fences(raw))
        data["general_news"] = to_list(data.get("general_news"))
        data["regulatory_news"] = to_list(data.get("regulatory_news"))
        log.info("[NewsEngine] News fetched for %r. general=%d regulatory=%d",
                 location, len(data["general_news"]), len(data["regulatory_news"]))
        return data
    except json.JSONDecodeError as e:
        log.error("[NewsEngine] JSON parse failed for %r: %s\nRaw response:\n%s",
                  location, e, locals().get("raw", "N/A"))
        return {
            "general_news": [{"title": "Data unavailable", "snippet": f"Could not retrieve news for {location}.", "source": "", "link": ""}],
            "regulatory_news": [{"title": "Data unavailable", "snippet": f"Could not retrieve RERA data for {location}.", "source": "", "link": ""}],
        }
    except AttributeError as e:
        log.error("[NewsEngine] Unexpected error for %r: %s", location, e)
        return {
            "general_news": [{"title": "Data unavailable", "snippet": f"Could not retrieve news for {location}.", "source": "", "link": ""}],
            "regulatory_news": [{"title": "Data unavailable", "snippet": f"Could not retrieve RERA data for {location}.", "source": "", "link": ""}],
        }
