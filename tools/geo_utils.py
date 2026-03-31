"""
LLM-based city → state resolver for India.

Results are cached with lru_cache so the same city never triggers
a second LLM call within a process lifetime.
"""

import json
import logging
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from tools.coerce import to_str, strip_markdown_fences

log = logging.getLogger(__name__)


def _get_llm() -> ChatOpenAI:
    # Small, fast model is fine — purely factual lookup
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)


@lru_cache(maxsize=256)
def resolve_city_state(city: str) -> dict:
    """
    Returns the Indian state/UT and RERA portal domain for any city.
    Result is cached — repeated calls for the same city cost nothing.

    Returns:
        {"state": "Maharashtra", "rera_portal": "maharera.mahaonline.gov.in"}
    """
    prompt = f"""You are an expert on Indian administrative geography and real estate regulation.

Given the city or locality name: "{city}"

Return:
1. "state" — the exact Indian state or union territory it belongs to
   (e.g. "Maharashtra", "Karnataka", "Delhi", "Uttar Pradesh")
2. "rera_portal" — the official RERA portal domain for that state
   (e.g. "maharera.mahaonline.gov.in", "rera.karnataka.gov.in", "up-rera.in")
   If you are not certain of the portal, use "rera.gov.in".

Respond with ONLY valid JSON (no markdown, no explanation):
{{"state": "<state>", "rera_portal": "<domain>"}}"""

    try:
        response = _get_llm().invoke([HumanMessage(content=prompt)])
        result = json.loads(strip_markdown_fences(response.content))
        state = to_str(result.get("state"), "")
        portal = to_str(result.get("rera_portal"), "rera.gov.in") or "rera.gov.in"
        if state:
            log.info("[GeoUtils] %r → state=%r portal=%r", city, state, portal)
            return {"state": state, "rera_portal": portal}
    except (json.JSONDecodeError, AttributeError) as e:
        log.error("[GeoUtils] resolve_city_state failed for %r: %s", city, e)

    log.warning("[GeoUtils] Falling back to India/rera.gov.in for city %r", city)
    return {"state": "India", "rera_portal": "rera.gov.in"}
