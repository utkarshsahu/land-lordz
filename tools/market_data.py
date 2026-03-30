"""
Fetches real estate market price trends and locality data for Indian cities
using SerpAPI (Google Search).
"""

import os
from serpapi import GoogleSearch


def get_market_overview(location: str, property_type: str) -> dict:
    """
    Search for current property prices and market trends in a location.
    Returns a dict with price range, trend summary, and raw snippets.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    query = f"{property_type} property price per sqft {location} 2024 real estate market trend"

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 5,
        "gl": "in",
        "hl": "en",
    }

    results = GoogleSearch(params).get_dict()
    snippets = []
    for r in results.get("organic_results", []):
        snippet = r.get("snippet", "")
        title = r.get("title", "")
        if snippet:
            snippets.append({"title": title, "snippet": snippet})

    return {
        "location": location,
        "property_type": property_type,
        "search_query": query,
        "market_snippets": snippets[:5],
    }


def get_locality_comparison(location: str) -> dict:
    """
    Get a comparison of sub-localities/micro-markets within the city.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    query = f"best localities to invest in {location} real estate 2024 appreciation"

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": 5,
        "gl": "in",
        "hl": "en",
    }

    results = GoogleSearch(params).get_dict()
    snippets = []
    for r in results.get("organic_results", []):
        snippet = r.get("snippet", "")
        title = r.get("title", "")
        if snippet:
            snippets.append({"title": title, "snippet": snippet})

    return {
        "location": location,
        "locality_snippets": snippets[:5],
    }
