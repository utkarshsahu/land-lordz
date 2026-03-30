"""
Searches for RERA-registered projects in a given city using SerpAPI.
RERA portals are state-specific in India; this tool searches publicly
available RERA data via Google since portals vary by state.
"""

import os
from serpapi import GoogleSearch

# Map of Indian states to their RERA portal domains (for targeted search)
RERA_PORTALS = {
    "Maharashtra": "maharera.mahaonline.gov.in",
    "Karnataka": "rera.karnataka.gov.in",
    "Delhi": "rera.delhi.gov.in",
    "Tamil Nadu": "tnrera.in",
    "Telangana": "rera.telangana.gov.in",
    "Gujarat": "gujrera.gujarat.gov.in",
    "Haryana": "haryanarera.gov.in",
    "Uttar Pradesh": "up-rera.in",
    "Rajasthan": "rera.rajasthan.gov.in",
    "West Bengal": "wbrera.wb.gov.in",
}

# City → State mapping for common metros
CITY_TO_STATE = {
    "mumbai": "Maharashtra",
    "pune": "Maharashtra",
    "nagpur": "Maharashtra",
    "bangalore": "Karnataka",
    "bengaluru": "Karnataka",
    "delhi": "Delhi",
    "noida": "Uttar Pradesh",
    "gurgaon": "Haryana",
    "gurugram": "Haryana",
    "chennai": "Tamil Nadu",
    "hyderabad": "Telangana",
    "ahmedabad": "Gujarat",
    "surat": "Gujarat",
    "jaipur": "Rajasthan",
    "kolkata": "West Bengal",
    "lucknow": "Uttar Pradesh",
}


def get_state_for_city(city: str) -> str:
    return CITY_TO_STATE.get(city.lower().strip(), "Maharashtra")


def search_rera_projects(location: str, property_type: str, budget_max_inr: float) -> list[dict]:
    """
    Search for RERA-registered projects matching the criteria.
    Returns a list of property dicts with name, builder, RERA ID, price estimate, etc.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    state = get_state_for_city(location)
    portal = RERA_PORTALS.get(state, "")

    budget_l = budget_max_inr / 100_000  # convert to Lakhs
    query = (
        f"RERA registered {property_type} projects {location} "
        f"under {budget_l:.0f} lakhs {state} RERA"
    )
    if portal:
        query += f" site:{portal} OR {query}"

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 8,
        "gl": "in",
        "hl": "en",
    }

    results = GoogleSearch(params).get_dict()
    projects = []

    for r in results.get("organic_results", []):
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        link = r.get("link", "")

        if not title:
            continue

        projects.append({
            "name": title,
            "description": snippet,
            "source_url": link,
            "location": location,
            "state": state,
            "property_type": property_type,
            # Placeholder financials — analyst agent will enrich these
            "price_inr": None,
            "area_sqft": None,
            "monthly_rent_inr": None,
            "rera_id": _extract_rera_id(snippet),
            "builder": _extract_builder(title),
        })

    return projects[:6]


def _extract_rera_id(text: str) -> str | None:
    """Attempt to extract a RERA registration ID from text."""
    import re
    # RERA IDs typically look like: P52100012345 or MahaRERA/P/123456
    patterns = [
        r"P\d{11}",
        r"[A-Z]{2,5}/P/\d+",
        r"RERA\s*(?:No\.?|ID:?)\s*([A-Z0-9/\-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _extract_builder(title: str) -> str:
    """Heuristically extract builder/developer name from result title."""
    keywords = ["by", "from", "developer", "builders", "realty", "projects"]
    title_lower = title.lower()
    for kw in keywords:
        idx = title_lower.find(kw)
        if idx != -1:
            return title[idx:].split("-")[0].strip()
    return title.split("-")[0].strip()
