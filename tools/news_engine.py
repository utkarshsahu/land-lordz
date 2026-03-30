"""
Fetches recent real estate news for a given location using SerpAPI.
"""

import os
from serpapi import GoogleSearch


def get_real_estate_news(location: str, max_results: int = 6) -> list[dict]:
    """
    Returns recent news articles about the real estate market in a city.
    Each item has: title, snippet, source, date (if available).
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    query = f"{location} real estate news property market 2024"

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "tbm": "nws",          # news tab
        "num": max_results,
        "gl": "in",
        "hl": "en",
    }

    results = GoogleSearch(params).get_dict()
    articles = []
    for item in results.get("news_results", []):
        articles.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "source": item.get("source", ""),
            "date": item.get("date", ""),
            "link": item.get("link", ""),
        })

    return articles[:max_results]


def get_regulatory_news(location: str) -> list[dict]:
    """
    Fetches recent RERA / regulatory policy news for the location.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    query = f"RERA {location} regulatory update builder compliance 2024"

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "tbm": "nws",
        "num": 4,
        "gl": "in",
        "hl": "en",
    }

    results = GoogleSearch(params).get_dict()
    articles = []
    for item in results.get("news_results", []):
        articles.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "source": item.get("source", ""),
            "date": item.get("date", ""),
        })

    return articles[:4]
