"""
Type-coercion helpers for LLM outputs.

LLMs can return numbers as strings ("8.75%", "65 Lakhs"), None where a list
is expected, dicts where a list is expected, etc. These helpers normalise
any LLM-produced value to the expected Python type with a safe fallback.
"""

import re


def to_float(value, default: float = 0.0) -> float:
    """
    Coerce value to float. Handles:
      - None           → default
      - int/float      → float(value)
      - "8.75%"        → 8.75  (strips non-numeric chars)
      - "65 Lakhs"     → 65.0  (strips trailing text)
      - dict/list      → default
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Extract the first numeric token (handles "8.75%", "Rs. 65,000", "~900 sqft")
        cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
        try:
            return float(cleaned) if cleaned else default
        except ValueError:
            return default
    return default


def to_str(value, default: str = "") -> str:
    """Coerce value to string. None → default, non-str → str(value)."""
    if value is None:
        return default
    return str(value).strip() if isinstance(value, str) else str(value)


def to_list(value, default: list | None = None) -> list:
    """
    Coerce value to list. Handles:
      - None   → default (or [])
      - list   → value
      - dict   → [value]  (LLM sometimes returns a single object instead of array)
      - other  → [value]
    """
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return default


def strip_markdown_fences(text: str) -> str:
    """
    Remove ```json ... ``` or ``` ... ``` wrapping that LLMs sometimes add.
    Safely handles missing closing fence.
    """
    text = text.strip()
    if not text.startswith("```"):
        return text
    # Remove opening fence line
    first_newline = text.find("\n")
    if first_newline == -1:
        return text  # just a fence with no content
    text = text[first_newline + 1:]
    # Remove closing fence if present
    if text.endswith("```"):
        text = text[: text.rfind("```")].rstrip()
    return text.strip()
