"""
Auditor Agent — validates data quality, flags risks, and checks RERA compliance signals.

LangGraph node signature: (state: AgentState) -> dict
Returns partial state update with: audit_report
"""

import logging
from state import AgentState

log = logging.getLogger(__name__)

_YIELD_FLOOR = 2.0      # below this is poor rental investment
_YIELD_CEILING = 8.0    # above this may be unrealistically optimistic
_CAP_RATE_FLOOR = 1.5
_PAYBACK_MAX = 40       # more than 40 years is a red flag


def _audit_property(analysis: dict) -> dict:
    flags = []
    warnings = []
    score = 100  # start at 100, deduct for issues

    fin = analysis.get("financials", {})
    prop = analysis.get("raw_property", {})

    # --- RERA checks ---
    rera_id = analysis.get("rera_id")
    if not rera_id:
        flags.append("No RERA ID found — verify registration before proceeding")
        score -= 20
    else:
        warnings.append(f"RERA ID detected: {rera_id} — verify on state portal")

    # --- Financial sanity ---
    yield_pct = fin.get("gross_rental_yield_pct", 0)
    if yield_pct < _YIELD_FLOOR:
        flags.append(f"Low rental yield ({yield_pct:.1f}%) — below investment-grade threshold of {_YIELD_FLOOR}%")
        score -= 15
    elif yield_pct > _YIELD_CEILING:
        warnings.append(f"Unusually high yield ({yield_pct:.1f}%) — verify rent estimate accuracy")
        score -= 5

    cap_rate = fin.get("cap_rate_pct", 0)
    if cap_rate < _CAP_RATE_FLOOR:
        flags.append(f"Cap rate too low ({cap_rate:.1f}%) — operating expenses may exceed rental income")
        score -= 10

    payback = fin.get("payback_years", 0)
    if payback > _PAYBACK_MAX:
        flags.append(f"Payback period too long ({payback:.0f} years)")
        score -= 10

    # --- Data completeness ---
    if not prop.get("price_inr"):
        warnings.append("Price was estimated — not sourced from listing; verify independently")
        score -= 5

    if not prop.get("area_sqft"):
        warnings.append("Area is estimated — obtain carpet area / super built-up from builder")
        score -= 5

    price_per_sqft = fin.get("price_per_sqft", 0)
    if price_per_sqft > 25000:
        warnings.append(f"High price per sqft (₹{price_per_sqft:,.0f}) — typical for premium micro-markets only")
    elif price_per_sqft < 2000:
        flags.append(f"Suspiciously low price per sqft (₹{price_per_sqft:,.0f}) — validate data")
        score -= 10

    risk_level = "LOW" if score >= 80 else "MEDIUM" if score >= 60 else "HIGH"

    return {
        "property_name": analysis["property_name"],
        "audit_score": max(score, 0),
        "risk_level": risk_level,
        "flags": flags,
        "warnings": warnings,
    }


def auditor_agent(state: AgentState) -> dict:
    analyses = state["financial_analyses"]
    log.info("[Auditor] Starting. %d properties to audit.", len(analyses))

    property_audits = [_audit_property(a) for a in analyses]

    for audit in property_audits:
        log.debug("[Auditor] %r → score=%d risk=%s flags=%s",
                  audit["property_name"], audit["audit_score"],
                  audit["risk_level"], audit["flags"])

    high_risk = [a for a in property_audits if a["risk_level"] == "HIGH"]
    medium_risk = [a for a in property_audits if a["risk_level"] == "MEDIUM"]
    low_risk = [a for a in property_audits if a["risk_level"] == "LOW"]

    shortlisted = [a["property_name"] for a in low_risk + medium_risk]
    log.info("[Auditor] Risk summary — HIGH: %d | MEDIUM: %d | LOW: %d | Shortlisted: %d",
             len(high_risk), len(medium_risk), len(low_risk), len(shortlisted))
    log.debug("[Auditor] Shortlisted properties: %s", shortlisted)

    audit_report = {
        "total_properties_reviewed": len(property_audits),
        "risk_summary": {
            "high": len(high_risk),
            "medium": len(medium_risk),
            "low": len(low_risk),
        },
        "property_audits": property_audits,
        "shortlisted": shortlisted,
    }

    return {"audit_report": audit_report}
