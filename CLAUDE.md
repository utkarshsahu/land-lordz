# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**land-lordz** is a Python multi-agent system for real estate market analysis, built on LangGraph. It uses specialized AI agents to analyze properties, scrape RERA data, fetch market data, and generate investment strategies.

## Tech Stack

- **LangGraph** — multi-agent orchestration and state machine
- **LangChain OpenAI** — LLM integration
- **Pandas** — data processing
- **Google Search Results** (`serpapi`) — web search
- **python-dotenv** — environment config

## Environment Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env` and add required keys:
- `OPENAI_API_KEY`
- `SERPAPI_API_KEY`

## Running the Project

```bash
python main.py
```

## Architecture

The system follows a LangGraph multi-agent pattern:

- **`state.py`** — defines the shared `TypedDict` state passed between all agents in the graph
- **`main.py`** — builds and compiles the LangGraph graph, defines edges/routing, and runs it
- **`agents/`** — each file exports a node function `(state) -> state` consumed by the graph:
  - `scout_agent.py` — discovers properties/listings using search and RERA data
  - `analyst_agent.py` — runs financial analysis on candidates
  - `auditor_agent.py` — validates data quality and flags risks
  - `strategist_agent.py` — synthesizes analysis into investment recommendations
- **`tools/`** — stateless utility functions called by agents:
  - `rera_scraper.py` — scrapes RERA (Real Estate Regulatory Authority) portal
  - `market_data.py` — fetches price trends and comparable data
  - `news_engine.py` — retrieves relevant real estate news
  - `finance_utils.py` — calculations (yield, cap rate, EMI, ROI, etc.)

Each agent is a pure function that reads from and writes to the shared `state` dict — no agent directly calls another agent.
