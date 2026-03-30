from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict):
    # --- Input ---
    query: str                          # raw user query, e.g. "2BHK in Pune under 80L"
    location: str                       # extracted city/area, e.g. "Pune"
    property_type: str                  # e.g. "2BHK", "3BHK", "villa"
    budget_max_inr: float               # max budget in INR

    # --- Scout output ---
    properties: List[Dict[str, Any]]    # list of candidate properties
    market_context: Dict[str, Any]      # price trends, locality data, recent news

    # --- Analyst output ---
    financial_analyses: List[Dict[str, Any]]  # per-property financial metrics

    # --- Auditor output ---
    audit_report: Dict[str, Any]        # risk flags and RERA compliance notes

    # --- Strategist output ---
    strategy_report: str                # final markdown recommendation text

    # --- Report ---
    report_path: str                    # path where the .md report was saved
