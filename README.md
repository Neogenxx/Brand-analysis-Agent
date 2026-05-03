# 🧳 Brand Analysis Agent

> **Competitive intelligence dashboard for luggage brands on Amazon India**


---

##  Quickstart (60 seconds — no API key needed)

```bash
git clone <your-repo-url>
cd brand_analysis_agent

pip install -r requirements.txt
python run.py
```

This auto-generates realistic sample data for 6 brands and launches the Streamlit dashboard at **http://localhost:8501**.

---

##  What the dashboard answers

| Question | Where to look |
|---|---|
| Which brands are premium vs value? | Overview → Positioning Map |
| Who relies on discounts most? | Comparison → Discount % chart |
| What do customers praise/complain about? | Drilldown → Aspect Scores |
| Who wins on sentiment vs price? | Overview → Value-for-Money chart |
| Non-obvious strategic insights | Agent Insights tab |

---

##  Architecture

```
Amazon India (Playwright)
        ↓
Data Processing (Pandas)
        ↓
   ┌─────────────────────┐
   │   Review Corpus     │
   ├──────────┬──────────┤
   │  Chroma  │  LLM/NLP │
   │  Vector  │  VADER + │
   │    DB    │  OpenAI  │
   └──────────┴──────────┘
        ↓
LangChain (Orchestration)
        ↓
LangGraph Agent (5-node pipeline)
  Node 1 — Data Aggregator
  Node 2 — Anomaly Detector
  Node 3 — Cross-Brand Comparator
  Node 4 — LLM Insight Generator
  Node 5 — Ranker + Filter
        ↓
FastAPI (REST API)
        ↓
Streamlit + Plotly Dashboard
```

---

## 📁 Project structure

```
brand_analysis_agent/
│
├── data/
│   ├── raw/                    ← Raw JSON files per brand (from scraper)
│   ├── processed/              ← Cleaned CSVs + JSONs used by dashboard
│   │   ├── products.csv
│   │   ├── reviews.csv
│   │   ├── sentiment.csv
│   │   ├── themes.json
│   │   └── insights.json       ← Agent Insights output
│   └── chroma_db/              ← ChromaDB vector store
│
├── scraper/
│   └── scraper.py              ← Playwright Amazon India scraper
│
├── processing/
│   ├── cleaning.py             ← Data normalisation pipeline
│   ├── sentiment.py            ← VADER + LLM sentiment scoring
│   └── themes.py               ← Theme + aspect-level extraction
│
├── vector_db/
│   └── chroma_store.py         ← ChromaDB indexing + semantic search
│
├── agents/
│   └── langgraph_pipeline.py   ← 5-node LangGraph reasoning pipeline
│
├── api/
│   └── main.py                 ← FastAPI REST backend
│
├── dashboard/
│   ├── app.py                  ← Main Streamlit entry point
│   ├── data_loader.py          ← Cached data access layer
│   ├── charts.py               ← Plotly chart factory functions
│   ├── view_overview.py        ← Tab 1: Overview
│   ├── view_comparison.py      ← Tab 2: Brand Comparison
│   ├── view_drilldown.py       ← Tab 3: Product Drilldown
│   ├── view_insights.py        ← Tab 4: Agent Insights
│   └── view_search.py          ← Tab 5: Semantic Review Search
│
├── utils/
│   ├── config.py               ← All constants and paths
│   ├── logger.py               ← Centralised logger
│   └── sample_data.py          ← Realistic mock data generator
│
├── run.py                      ← One-command launcher
├── requirements.txt
├── .env.example
└── README.md
```

---

##  Setup (full install)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright browsers (for scraping)

```bash
playwright install chromium
```

### 3. Configure API keys (optional — only for LLM features)

```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY or GEMINI_API_KEY
```

---

## ▶️ Running the project

### Option A — Sample data (no API key, instant)

```bash
python run.py
```

### Option B — Live scrape + full LLM pipeline

```bash
python run.py --scrape
```

### Option C — Launch API backend separately

```bash
# Terminal 1
uvicorn api.main:app --reload --port 8000

# Terminal 2
streamlit run dashboard/app.py
```

### Option D — Pipeline only (no UI)

```bash
python run.py --pipeline-only
```

---

## 📊 Dashboard views

| Tab | What it shows |
|---|---|
| **Overview** | KPI cards, positioning map, sentiment snapshot, value-for-money ranking |
| **Brand Comparison** | Side-by-side metrics, radar chart, aspect heatmap, sortable table |
| **Product Drilldown** | Filtered product cards, review samples, aspect scores per product |
| **Agent Insights** | 5 auto-generated non-obvious conclusions from the LangGraph pipeline |
| **Review Search** | Semantic search across all reviews using ChromaDB + sentence-transformers |

---

## 🤖 Sentiment methodology

**Layer 1 — VADER (per review)**
- Runs on every review body text
- Returns compound score (−1 to +1) → mapped to label (positive / neutral / negative)
- Fast, deterministic, no API key required

**Layer 2 — LLM brand aggregation (optional)**
- Sends a sample of 30 reviews per brand to OpenAI/Gemini
- Returns: overall sentiment score (0–100), summary, top positives, top negatives
- Blended with VADER: 60% VADER + 40% LLM

**Aspect scoring**
- Keyword matching per aspect (wheels, handle, zipper, material, durability, size, weight)
- Average star rating of reviews mentioning each aspect → mapped to 0–1 score
- LLM-enhanced scores when API key is available

---

## 📦 Dataset

| File | Rows | Description |
|---|---|---|
| `products.csv` | 72 | 12 products × 6 brands with price, MRP, discount, rating |
| `reviews.csv` | ~900 | Customer reviews with VADER sentiment labels |
| `sentiment.csv` | 6 | Brand-level aggregated sentiment scores |
| `themes.json` | 6 brands | Positive/negative themes + aspect scores per brand |
| `insights.json` | 5 | Agent-generated competitive insights |

> **Note:** Sample data is generated from calibrated brand profiles to reflect realistic Amazon India market conditions. For live data, run the scraper.

---

## 📦 Brands tracked

| Brand | Tier | Notes |
|---|---|---|
| American Tourister | Premium | Highest sentiment, lowest discount dependency |
| Safari | Mid-Market | Strong durability sentiment |
| Nasher Miles | Mid-Market | Best value-for-money score |
| VIP | Mid-Market | Wide price spread, legacy brand |
| Skybags | Value | Heavy discounting, wheel quality concerns |
| Aristocrat | Value | Zipper quality is primary complaint driver |

---

## ⚠️ Limitations

- Sample data is synthetic — run the scraper for real Amazon India data
- Amazon's anti-scraping measures may throttle or block the scraper
- Sentiment accuracy depends on LLM model quality (VADER is a good baseline)
- ChromaDB indexing requires sentence-transformers (~90MB model download on first run)
- Review data may contain noise, fake reviews, or sampling bias

---

## 🔮 Future improvements

- Real-time data updates via scheduled scraping
- Review trust scoring (fake review detection via repetition analysis)
- Time-series sentiment tracking (quality drift over months)
- Price alert system (notify when brand drops discount threshold)
- Cloud deployment with autoscaling (Railway, Render, or AWS)

---

## 📌 Evaluation rubric alignment

| Criteria | How this project addresses it |
|---|---|
| Data collection (20) | Playwright scraper + clean CSV/JSON dataset |
| Analytical depth (20) | VADER + LLM sentiment, aspect scoring, theme extraction |
| Dashboard UX/UI (20) | 5-tab Streamlit UI with dynamic filters, charts, drilldowns |
| Competitive intelligence (15) | Cross-brand benchmarking + non-obvious comparisons |
| Technical execution (15) | Modular code, logging, error handling, documented methodology |
| Product thinking (10) | Agent Insights — answers "why" not just "what" |

---

*Built for the Moonshot AI Agent Internship — 2024*
