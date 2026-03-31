"""
Analyst Agent — enriches properties with financial metrics.

LangGraph node signature: (state: AgentState) -> dict
Returns partial state update with: financial_analyses

LLM calls: 1 (batch estimation for all properties missing price data)
Home loan rate: read from market_context set by scout — no extra fetch.
"""

import json
import logging
import traceback
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from state import AgentState
from tools.finance_utils import full_financial_profile
from tools.coerce import to_float, strip_markdown_fences

log = logging.getLogger(__name__)

_llm = None


def _get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _llm


def _batch_estimate_financials(
    properties: list[dict], location: str, budget_max_inr: float
) -> dict[int, dict]:
    items = [
        {
            "index": i,
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "property_type": p.get("property_type", ""),
        }
        for i, p in enumerate(properties)
    ]

    log.debug("[Analyst] Batch estimation input (%d properties):\n%s", len(items), json.dumps(items, indent=2))

    prompt = f"""You are an Indian real estate pricing expert. Estimate realistic financials
for ALL {len(items)} properties listed below in {location}.
Budget ceiling for buyer: ₹{budget_max_inr/1e5:.0f} Lakhs.

Properties:
{json.dumps(items, indent=2)}

For each property estimate:
- price_inr: realistic market price in INR (must not exceed budget ceiling)
- monthly_rent_inr: achievable monthly rent in INR
- area_sqft: carpet area in sqft
- rent_rationale: one sentence citing comparable micro-market lease rates
  (e.g. "Similar 2BHK units in [locality] lease at ₹18–22/sqft/month per Anarock data.")

Keep estimates internally consistent — if one project is clearly more premium,
price it proportionally higher. Base estimates on known {location} micro-market rates.

Respond ONLY with a JSON array (no explanation, no markdown):
[{{"index": 0, "price_inr": number, "monthly_rent_inr": number, "area_sqft": number, "rent_rationale": "..."}}, ...]"""

    raw_response = None
    try:
        response = _get_llm().invoke([HumanMessage(content=prompt)])
        raw_response = response.content
        log.debug("[Analyst] Raw LLM response for batch estimation:\n%s", raw_response)

        cleaned = strip_markdown_fences(raw_response)
        estimates_list = json.loads(cleaned)
        log.info("[Analyst] Batch estimation succeeded for %d properties.", len(estimates_list))

        result = {}
        for item in estimates_list:
            idx = item.get("index")
            if idx is None:
                log.warning("[Analyst] Estimate item missing 'index' key, skipping: %s", item)
                continue
            # Coerce all numeric fields — LLM may return strings like "65 Lakhs"
            result[int(idx)] = {
                "index": int(idx),
                "price_inr": to_float(item.get("price_inr"), 0.0) or None,
                "monthly_rent_inr": to_float(item.get("monthly_rent_inr"), 0.0) or None,
                "area_sqft": to_float(item.get("area_sqft"), 0.0) or None,
                "rent_rationale": item.get("rent_rationale", ""),
            }
        return result

    except json.JSONDecodeError as e:
        log.error(
            "[Analyst] JSON parse failed for batch estimation.\n"
            "  Error: %s\n"
            "  Raw LLM response was:\n%s",
            e, raw_response
        )
    except KeyError as e:
        log.error(
            "[Analyst] Missing key %s in LLM estimate item.\n"
            "  Raw LLM response was:\n%s",
            e, raw_response
        )
    except Exception as e:
        log.error("[Analyst] Unexpected error in batch estimation:\n%s", traceback.format_exc())

    # Fallback: uniform estimate for all
    fallback_price = budget_max_inr * 0.85
    log.warning("[Analyst] Using fallback estimates: price=₹%.0f, rent=₹%.0f, area=900sqft",
                fallback_price, round(fallback_price * 0.003))
    return {
        i: {
            "price_inr": fallback_price,
            "monthly_rent_inr": round(fallback_price * 0.003),
            "area_sqft": 900,
        }
        for i in range(len(properties))
    }


def analyst_agent(state: AgentState) -> dict:
    properties = state["properties"]
    location = state["location"]
    budget_max_inr = state["budget_max_inr"]

    log.info("[Analyst] Starting. %d properties received from scout.", len(properties))

    # Home loan rate already fetched by scout — no extra LLM call
    home_loan_rate_pct = state["market_context"].get("home_loan_rate_pct", 8.75)
    log.info("[Analyst] Home loan rate from market_context: %s%%", home_loan_rate_pct)

    # Log what scout found
    for i, p in enumerate(properties):
        log.debug(
            "[Analyst] Property %d: name=%r | price_inr=%s | area_sqft=%s | rent=%s",
            i, p.get("name"), p.get("price_inr"), p.get("area_sqft"), p.get("monthly_rent_inr")
        )

    # Identify which properties need financial estimation.
    # monthly_rent_inr is always None from the scraper (rent never appears in listings),
    # so any property missing rent — regardless of whether price was scraped — needs estimation.
    needs_estimate = [p for p in properties if not p.get("price_inr") or not p.get("monthly_rent_inr")]
    log.info("[Analyst] %d/%d properties need estimation (missing price or rent).",
             len(needs_estimate), len(properties))

    if needs_estimate:
        estimates_by_idx = _batch_estimate_financials(needs_estimate, location, budget_max_inr)
        for i, prop in enumerate(needs_estimate):
            if i in estimates_by_idx:
                est = estimates_by_idx[i]
                prop.update(est)
                log.debug("[Analyst] Estimated for %r: %s", prop.get("name"), est)
            else:
                log.warning("[Analyst] No estimate returned for property index %d (%r).", i, prop.get("name"))

    financial_analyses = []
    for prop in properties:
        prop_name = prop.get("name", "Unknown")
        log.debug("[Analyst] Computing financial profile for %r (price_inr=%s)", prop_name, prop.get("price_inr"))
        try:
            profile = full_financial_profile(prop, home_loan_rate_pct=home_loan_rate_pct)
            log.debug("[Analyst] Profile for %r: %s", prop_name, profile)
            financial_analyses.append({
                "property_name": prop_name,
                "location": prop.get("location", location),
                "rera_id": prop.get("rera_id"),
                "builder": prop.get("builder"),
                "source_url": prop.get("source_url"),
                "financials": profile,
                "raw_property": prop,
            })
        except Exception:
            log.error("[Analyst] Failed to compute profile for %r:\n%s", prop_name, traceback.format_exc())

    log.info("[Analyst] Done. %d financial profiles computed.", len(financial_analyses))
    return {"financial_analyses": financial_analyses}
