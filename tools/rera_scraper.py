"""
Searches for RERA-registered projects in a given city using SerpAPI.
RERA portals are state-specific in India; this tool searches publicly
available RERA data via Google since portals vary by state.
"""

import os
from serpapi import GoogleSearch
from tools.geo_utils import resolve_city_state


def search_rera_projects(location: str, property_type: str, budget_max_inr: float) -> list[dict]:
    """
    Search for RERA-registered projects matching the criteria.
    Returns a list of property dicts with name, builder, RERA ID, price estimate, etc.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    geo = resolve_city_state(location)
    state = geo["state"]
    portal = geo["rera_portal"]

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

        if not _is_property_listing(title, link, snippet):
            continue

        combined_text = f"{title} {snippet}"
        projects.append({
            "name": title,
            "description": snippet,
            "source_url": link,
            "location": location,
            "state": state,
            "property_type": property_type,
            # Attempt extraction from snippet; analyst LLM fills gaps if None
            "price_inr": _extract_price_inr(combined_text),
            "area_sqft": _extract_area_sqft(combined_text),
            "monthly_rent_inr": None,  # rent data rarely in listings; always LLM-estimated
            "rera_id": _extract_rera_id(snippet),
            "builder": _extract_builder(title),
        })

    return projects[:6]


def _is_property_listing(title: str, link: str, snippet: str) -> bool:
    """
    Returns True only if the result looks like an actual property listing or project page,
    not a blog post, news article, or informational guide.
    """
    blog_url_patterns = [
        "/blog/", "/news/", "/articles/", "/article/", "/guide/", "/tips/",
        "/advice/", "/insights/", "magicbricks.com/blog", "99acres.com/articles",
        "housing.com/news", "economictimes.indiatimes.com",
    ]
    blog_title_signals = [
        "guide", "tips", "how to", "what is", "top 10", "best ", "review",
        "explained", "checklist", "things to know", "should you", "complete",
        "steps to", "everything you", "pros and cons", "vs ", " or ", "reasons why",
    ]
    listing_signals = [
        "bhk", "sqft", "sq ft", "sq.ft", "apartment", "flat", "floor plan",
        "possession", "launch", "configuration", "crore", "lakh", "rera",
        "project", "residency", "residences", "heights", "tower", "enclave",
    ]

    combined_lower = (title + " " + snippet + " " + link).lower()

    for p in blog_url_patterns:
        if p in link.lower():
            return False

    title_lower = title.lower()
    has_blog_signal = any(sig in title_lower for sig in blog_title_signals)
    has_listing_signal = any(sig in combined_lower for sig in listing_signals)

    # Reject only when it looks clearly like editorial content and has no listing signals
    if has_blog_signal and not has_listing_signal:
        return False

    return True


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


def _extract_price_inr(text: str) -> float | None:
    """
    Extract property price from snippet text.
    Handles formats like: ₹65L, Rs.1.2Cr, 80 lakhs, 1.5 crore, starting at 45L, etc.
    Returns value in INR, or None if not found.
    """
    import re

    text_lower = text.lower()

    # Crore patterns: 1.2 cr / 1.2 crore / Rs 1.2Cr
    cr_match = re.search(r"(?:₹|rs\.?\s*)?([\d.]+)\s*cr(?:ore)?", text_lower)
    if cr_match:
        return float(cr_match.group(1)) * 1_00_00_000

    # Lakh patterns: 65L / 65 lakh / ₹65 lakhs
    lakh_match = re.search(r"(?:₹|rs\.?\s*)?([\d.]+)\s*l(?:akh)?", text_lower)
    if lakh_match:
        return float(lakh_match.group(1)) * 1_00_000

    return None


def _extract_area_sqft(text: str) -> float | None:
    """
    Extract area from snippet text.
    Handles: 950 sqft, 1200 sq.ft, 850 sq ft, etc.
    Returns area as float, or None if not found.
    """
    import re

    match = re.search(r"([\d,]+)\s*sq\.?\s*ft", text.lower())
    if match:
        return float(match.group(1).replace(",", ""))
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
