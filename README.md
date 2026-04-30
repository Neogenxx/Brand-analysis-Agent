# 📊 AI-Powered Competitive Intelligence Dashboard

### Luggage Brands Analysis (Amazon India)

---

## 🚀 Project Overview

This project is an **AI-powered competitive intelligence system** that analyzes luggage brands on Amazon India by combining:

* Product pricing data
* Customer reviews
* Sentiment and thematic analysis

The system transforms **unstructured marketplace data into actionable insights** through an interactive dashboard and an agent-based reasoning layer.

---

## 🎯 Objective

To build a decision-ready dashboard that answers:

* Which brands are premium vs value-focused?
* Which brands rely on discounts to drive demand?
* What customers consistently praise or complain about?
* Which brands offer the best value for money?

---

## 🧰 Tech Stack

### Core AI & Backend

* Python (3.10+)
* LangChain
* LangGraph
* FastAPI

### Data Processing

* Pandas

### Web Scraping

* Playwright

### LLM / NLP

* OpenAI / Gemini (for sentiment analysis, summarization, and insights)

### Vector Database

* Chroma (for storing review embeddings and semantic retrieval)

### Frontend & Visualization

* Streamlit
* Plotly

---

## 🏗️ System Architecture

```
Amazon Scraper (Playwright)
        ↓
Data Processing (Pandas)
        ↓
Vector DB (Chroma)
        ↓
AI Layer (LangChain)
        ↓
Agent Layer (LangGraph)
        ↓
API Layer (FastAPI)
        ↓
Dashboard (Streamlit + Plotly)
```

---

## 🔄 Workflow

### 1. Data Collection

* Scrape product listings and reviews from Amazon India
* Extract:

  * Product name, price, MRP, discount
  * Ratings and review text

---

### 2. Data Processing

* Clean and normalize data
* Structure into a usable dataset (CSV/JSON)

---

### 3. Embedding & Storage

* Convert reviews into embeddings
* Store in vector database (Chroma) for semantic retrieval

---

### 4. Sentiment & Theme Analysis

* Perform sentiment classification (positive, negative, neutral)
* Extract recurring themes:

  * durability, wheels, handle, material, zipper

---

### 5. Analytical Computation

* Average price per brand
* Average discount
* Rating distribution
* Sentiment score

#### Derived Metric

* **Value-for-Money Score** (sentiment vs price positioning)

---

### 6. Agent Workflow (LangGraph)

A multi-step reasoning pipeline generates high-quality insights:

* Review summarization
* Theme extraction
* Sentiment aggregation
* Cross-brand comparison
* Insight generation

---

### 7. API Layer

* Built using FastAPI
* Serves processed data and triggers agent insights

---

### 8. Dashboard

Interactive UI built with Streamlit:

* Dynamic filters (brand, price, rating, sentiment)
* Interactive charts (Plotly)
* Drilldown capabilities

---

## 📊 Dashboard Features

### 1. Overview

* Total brands, products, reviews
* Average sentiment and pricing snapshot

---

### 2. Brand Comparison

* Price, discount, rating, sentiment
* Top pros and cons
* Side-by-side benchmarking

---

### 3. Product Drilldown

* Product-level details
* Review summaries
* Key strengths and complaints

---

### 4. Agent Insights (Key Feature)

* Auto-generated insights such as:

  * Overpriced brands
  * Value leaders
  * Hidden product weaknesses

---

## 🤖 Key Highlights

* End-to-end AI pipeline
* Agent-based reasoning using LangGraph
* Vector database integration for semantic understanding
* Aspect-based sentiment analysis
* Interactive and decision-focused dashboard

---

## ▶️ How to Run

### 1. Clone Repository

```bash
git clone <your-repo-link>
cd <project-folder>
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Backend (FastAPI)

```bash
uvicorn app.main:app --reload
```

### 4. Run Dashboard

```bash
streamlit run dashboard/app.py
```

---

## 📂 Project Structure

```
project/
│
├── data/
│   ├── raw/
│   ├── processed/
│
├── scraper/
│   └── scraper.py
│
├── processing/
│   ├── cleaning.py
│   ├── sentiment.py
│   └── themes.py
│
├── vector_db/
│   └── chroma_store.py
│
├── agents/
│   └── langgraph_pipeline.py
│
├── api/
│   └── main.py
│
├── dashboard/
│   └── app.py
│
├── utils/
│
├── requirements.txt
└── README.md
```

---

## ⚠️ Limitations

* Limited sample size due to scraping constraints
* Review data may contain noise or bias
* Sentiment accuracy depends on model quality
* Amazon anti-scraping restrictions may affect scalability

---

## 🔮 Future Improvements

* Aspect-level sentiment scoring (per feature)
* Advanced anomaly detection
* Review trust analysis (fake review detection)
* Real-time data updates
* Deployment on cloud with autoscaling

---

## 🎥 Demo

(Optional) Add Loom / demo video link here

---

## 📌 Conclusion

This project demonstrates how AI can transform raw e-commerce data into:

> **Actionable competitive intelligence**

By combining data engineering, LLMs, vector databases, and agent-based reasoning, the system provides insights that help decision-makers understand **who is winning in the market and why**.

---
