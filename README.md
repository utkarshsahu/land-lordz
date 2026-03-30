# land-lordz

Indian real estate investment analyser powered by a LangGraph multi-agent pipeline. Given a natural language query (city, property type, budget), it searches RERA-registered projects, computes financial metrics, audits risks, and produces a structured Markdown investment report.

## How it works

```
POST /analyze
      │
      ▼
  Scout Agent        ← SerpAPI: RERA projects, market prices, news
      │
      ▼
  Analyst Agent      ← GPT-4o-mini: estimate missing prices; compute EMI, yield, cap rate
      │
      ▼
  Auditor Agent      ← Rule-based: RERA ID check, yield sanity, risk scoring
      │
      ▼
  Strategist Agent   ← GPT-4o: ranked property list + investment recommendation
      │
      ▼
  reports/<city>_<timestamp>.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Add your API keys to `.env`:

```
OPENAI_API_KEY=...
SERPAPI_API_KEY=...
```

Get a SerpAPI key at [serpapi.com](https://serpapi.com) (free tier: 100 searches/month).

## Running

```bash
python main.py
# Server starts at http://localhost:8000
```

## API

### `POST /analyze`

```json
{
  "query": "2BHK in Pune under 80L",
  "location": "Pune",
  "property_type": "2BHK",
  "budget_max_inr": 8000000
}
```

**Response:**

```json
{
  "status": "success",
  "report_path": "reports/pune_20240101_120000.md",
  "summary": "..."
}
```

The full report is saved to `reports/`. The response `summary` is the opening paragraph of the report.

### `GET /health`

Returns `{"status": "ok"}`.

## Supported Cities

RERA portal search is tuned for: Mumbai, Pune, Bangalore, Delhi, Noida, Gurgaon, Chennai, Hyderabad, Ahmedabad, Jaipur, Kolkata, Lucknow, Surat, Nagpur.

## Project Structure

```
├── main.py                  FastAPI app + LangGraph graph
├── state.py                 Shared AgentState TypedDict
├── agents/
│   ├── scout_agent.py       Property discovery + market context
│   ├── analyst_agent.py     Financial metrics (EMI, yield, cap rate, payback)
│   ├── auditor_agent.py     Risk scoring and RERA compliance checks
│   └── strategist_agent.py  Final ranked report via LLM
└── tools/
    ├── finance_utils.py     Pure financial calculations (no I/O)
    ├── market_data.py       Price trends and locality comparison
    ├── news_engine.py       Real estate and regulatory news
    └── rera_scraper.py      RERA project search, state-portal aware
```

## Financial Metrics Computed

| Metric | Description |
|--------|-------------|
| Price per sqft | ₹/sqft vs market benchmark |
| EMI | Monthly loan repayment at 8.5% for 20 years (80% LTV) |
| Gross rental yield | Annual rent / property price × 100 |
| Cap rate | NOI / property price × 100 |
| Payback period | Years to recover investment via rent + 5% annual appreciation |
| Stamp duty + registration | State-specific estimates (Maharashtra, Karnataka, Delhi, etc.) |

## Risk Audit Flags

The auditor scores each property 0–100 and assigns LOW / MEDIUM / HIGH risk based on:

- Missing or unverified RERA registration ID
- Rental yield below 2% or above 8%
- Cap rate below 1.5%
- Payback period above 40 years
- Price per sqft outside plausible range
- Estimated (not scraped) price or area
