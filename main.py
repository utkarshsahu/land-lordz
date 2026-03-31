"""
land-lordz — Indian Real Estate Investment Analyser
FastAPI entry point + LangGraph orchestration

POST /analyze
  Body: { "query": str, "location": str, "property_type": str, "budget_max_inr": float }
  Returns: { "status": str, "report_path": str, "summary": str }
"""

import logging
import os
import re
import traceback
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END

from state import AgentState
from agents.scout_agent import scout_agent
from agents.analyst_agent import analyst_agent
from agents.auditor_agent import auditor_agent
from agents.strategist_agent import strategist_agent

load_dotenv()

# ---------------------------------------------------------------------------
# Logging setup — INFO by default, DEBUG if LOG_LEVEL=DEBUG in env
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

app = FastAPI(
    title="land-lordz",
    description="Indian real estate investment analysis powered by LangGraph multi-agent AI",
    version="1.0.0",
)

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Natural language query, e.g. '2BHK in Pune under 80L'")
    location: str = Field(..., description="City or area, e.g. 'Pune', 'Bangalore'")
    property_type: str = Field(default="2BHK", description="Property type, e.g. '2BHK', '3BHK', 'villa'")
    budget_max_inr: float = Field(..., description="Maximum budget in INR, e.g. 8000000 for 80L")


class AnalyzeResponse(BaseModel):
    status: str
    report_path: str
    summary: str


# ---------------------------------------------------------------------------
# LangGraph graph builder
# ---------------------------------------------------------------------------

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("scout", scout_agent)
    graph.add_node("analyst", analyst_agent)
    graph.add_node("auditor", auditor_agent)
    graph.add_node("strategist", strategist_agent)

    graph.add_edge(START, "scout")
    graph.add_edge("scout", "analyst")
    graph.add_edge("analyst", "auditor")
    graph.add_edge("auditor", "strategist")
    graph.add_edge("strategist", END)

    return graph.compile()


_graph = build_graph()


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def save_report(state: AgentState, request: AnalyzeRequest) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_location = re.sub(r"[^a-zA-Z0-9_]", "_", request.location.lower())
    filename = f"{safe_location}_{timestamp}.md"
    filepath = REPORTS_DIR / filename

    header = f"""# Real Estate Investment Report
    **Query:** {request.query}. 
    **Location:** {request.location}. 
    **Property Type:** {request.property_type}. 
    **Budget:** ₹{request.budget_max_inr / 1e5:.0f} Lakhs. 
    **Generated:** {datetime.now().strftime("%B %d, %Y %H:%M")}. 
    ---"""

    filepath.write_text(header + state["strategy_report"], encoding="utf-8")
    return str(filepath)

# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    # Validate required env vars
    missing = [k for k in ("OPENAI_API_KEY", "SERPAPI_API_KEY") if not os.getenv(k)]
    if missing:
        raise HTTPException(status_code=500, detail=f"Missing env vars: {', '.join(missing)}")

    initial_state: AgentState = {
        "query": request.query,
        "location": request.location,
        "property_type": request.property_type,
        "budget_max_inr": request.budget_max_inr,
        # Fields populated by agents
        "properties": [],
        "market_context": {},
        "financial_analyses": [],
        "audit_report": {},
        "strategy_report": "",
        "report_path": "",
    }

    log.info("[API] /analyze request — location=%r type=%r budget=%.0fL",
             request.location, request.property_type, request.budget_max_inr / 1e5)
    try:
        final_state: AgentState = _graph.invoke(initial_state)
    except Exception as e:
        log.error("[API] Agent pipeline failed:\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {str(e)}")

    report_path = save_report(final_state, request)

    # Extract first paragraph of the strategy report as summary
    lines = final_state["strategy_report"].strip().splitlines()
    summary_lines = []
    for line in lines:
        if line.strip():
            summary_lines.append(line.strip())
        if len(summary_lines) >= 3:
            break
    summary = " ".join(summary_lines)

    return AnalyzeResponse(
        status="success",
        report_path=report_path,
        summary=summary,
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug")
