"""
main.py  —  FastAPI REST API
Serves cleaned data, aggregated metrics, themes, and agent insights
to the Streamlit dashboard (and any other client).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from utils.config import DATA_PROCESSED_PATH, BRANDS, API_HOST, API_PORT
from utils.logger import get_logger

logger = get_logger("api")

app = FastAPI(
    title="Brand Analysis Agent API",
    description="Competitive intelligence API for luggage brands on Amazon India",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Data loaders (cached in memory on startup) ────────────────────────────────

_cache: dict = {}


def _load_csv(name: str) -> pd.DataFrame:
    if name in _cache:
        return _cache[name]
    path = DATA_PROCESSED_PATH / name
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    _cache[name] = df
    return df


def _load_json(name: str) -> dict | list:
    if name in _cache:
        return _cache[name]
    path = DATA_PROCESSED_PATH / name
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache[name] = data
    return data


def _clear_cache():
    _cache.clear()


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "Brand Analysis Agent API"}


@app.get("/api/health", tags=["health"])
def health():
    products_df  = _load_csv("products.csv")
    reviews_df   = _load_csv("reviews.csv")
    sentiment_df = _load_csv("sentiment.csv")
    return {
        "status":         "ok",
        "brands":         BRANDS,
        "products_count": len(products_df),
        "reviews_count":  len(reviews_df),
        "sentiment_rows": len(sentiment_df),
        "data_path":      str(DATA_PROCESSED_PATH),
    }


# ── Brands ────────────────────────────────────────────────────────────────────

@app.get("/api/brands", tags=["brands"])
def get_brands():
    df = _load_csv("products.csv")
    if df.empty:
        return {"brands": BRANDS}
    return {"brands": sorted(df["brand"].unique().tolist())}


@app.get("/api/brands/{brand}", tags=["brands"])
def get_brand_detail(brand: str):
    products_df  = _load_csv("products.csv")
    sentiment_df = _load_csv("sentiment.csv")
    themes       = _load_json("themes.json")

    bp = products_df[products_df["brand"] == brand]
    if bp.empty:
        raise HTTPException(404, f"Brand '{brand}' not found")

    bs = sentiment_df[sentiment_df["brand"] == brand]

    return {
        "brand":            brand,
        "avg_price":        round(bp["price"].mean(), 0),
        "min_price":        round(bp["price"].min(), 0),
        "max_price":        round(bp["price"].max(), 0),
        "avg_discount":     round(bp["discount_pct"].mean(), 1),
        "avg_rating":       round(bp["rating"].mean(), 2),
        "total_products":   len(bp),
        "sentiment_score":  round(float(bs["sentiment_score"].mean()), 1) if not bs.empty else None,
        "positive_pct":     round(float(bs["positive_pct"].mean()), 1)    if not bs.empty else None,
        "negative_pct":     round(float(bs["negative_pct"].mean()), 1)    if not bs.empty else None,
        "themes":           themes.get(brand, {}),
        "products":         bp.to_dict(orient="records"),
    }


# ── Products ──────────────────────────────────────────────────────────────────

@app.get("/api/products", tags=["products"])
def get_products(
    brand:      Optional[str]   = Query(None),
    min_price:  Optional[float] = Query(None),
    max_price:  Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None),
    size:       Optional[str]   = Query(None),
    sort_by:    str             = Query("price"),
    ascending:  bool            = Query(True),
):
    df = _load_csv("products.csv")
    if df.empty:
        return {"products": [], "total": 0}

    if brand:
        df = df[df["brand"] == brand]
    if min_price is not None:
        df = df[df["price"] >= min_price]
    if max_price is not None:
        df = df[df["price"] <= max_price]
    if min_rating is not None:
        df = df[df["rating"] >= min_rating]
    if size:
        df = df[df["size_category"].str.contains(size, case=False, na=False)]

    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=ascending)

    return {"products": df.to_dict(orient="records"), "total": len(df)}


# ── Comparison ────────────────────────────────────────────────────────────────

@app.get("/api/comparison", tags=["comparison"])
def get_comparison(brands: Optional[str] = Query(None)):
    products_df  = _load_csv("products.csv")
    sentiment_df = _load_csv("sentiment.csv")
    themes       = _load_json("themes.json")

    brand_list = brands.split(",") if brands else BRANDS

    rows = []
    for brand in brand_list:
        bp = products_df[products_df["brand"] == brand]
        bs = sentiment_df[sentiment_df["brand"] == brand]
        if bp.empty:
            continue
        t = themes.get(brand, {})
        asp = t.get("aspect_scores", {})

        rows.append({
            "brand":           brand,
            "avg_price":       round(bp["price"].mean(), 0),
            "avg_discount":    round(bp["discount_pct"].mean(), 1),
            "avg_rating":      round(bp["rating"].mean(), 2),
            "total_reviews":   int(bp["review_count"].sum()),
            "sentiment_score": round(float(bs["sentiment_score"].mean()), 1) if not bs.empty else 0,
            "positive_pct":    round(float(bs["positive_pct"].mean()), 1)    if not bs.empty else 0,
            "negative_pct":    round(float(bs["negative_pct"].mean()), 1)    if not bs.empty else 0,
            "top_positives":   t.get("positive_themes", [])[:3],
            "top_negatives":   t.get("negative_themes", [])[:3],
            "wheels_score":    asp.get("wheels"),
            "handle_score":    asp.get("handle"),
            "zipper_score":    asp.get("zipper"),
            "durability_score":asp.get("durability"),
            "weight_score":    asp.get("weight"),
            "value_for_money": round(
                float(bs["sentiment_score"].mean()) /
                max(bp["price"].mean(), 1) * 1000, 3
            ) if not bs.empty else 0,
        })

    return {"comparison": rows}


# ── Insights ──────────────────────────────────────────────────────────────────

@app.get("/api/insights", tags=["insights"])
def get_insights():
    insights = _load_json("insights.json")
    if not insights:
        return {"insights": [], "message": "Run the agent pipeline to generate insights."}
    return {"insights": insights}


@app.post("/api/insights/refresh", tags=["insights"])
def refresh_insights():
    """Trigger the LangGraph pipeline to regenerate insights."""
    try:
        from agents.langgraph_pipeline import run_pipeline
        _clear_cache()
        insights = run_pipeline()
        return {"status": "ok", "insights_count": len(insights)}
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ── Themes ────────────────────────────────────────────────────────────────────

@app.get("/api/themes", tags=["themes"])
def get_all_themes():
    return {"themes": _load_json("themes.json")}


@app.get("/api/themes/{brand}", tags=["themes"])
def get_brand_themes(brand: str):
    themes = _load_json("themes.json")
    if brand not in themes:
        raise HTTPException(404, f"Themes not found for '{brand}'")
    return {"brand": brand, "themes": themes[brand]}


# ── Semantic search ───────────────────────────────────────────────────────────

@app.get("/api/search", tags=["search"])
def semantic_search(
    q:          str            = Query(..., description="Search query"),
    brand:      Optional[str]  = Query(None),
    n_results:  int            = Query(10),
    sentiment:  Optional[str]  = Query(None),
):
    try:
        from vector_db.chroma_store import query_reviews
        results = query_reviews(q, brand=brand, n_results=n_results, sentiment=sentiment)
        return {"query": q, "results": results}
    except Exception as exc:
        raise HTTPException(500, f"Search error: {exc}")


# ── Trigger pipeline steps ────────────────────────────────────────────────────

@app.post("/api/pipeline/sample-data", tags=["pipeline"])
def generate_sample_data():
    """Generate sample data (no scraping needed)."""
    try:
        from utils.sample_data import save_sample_data
        _clear_cache()
        save_sample_data()
        return {"status": "ok", "message": "Sample data generated successfully"}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.post("/api/pipeline/run-all", tags=["pipeline"])
def run_full_pipeline(use_llm: bool = Query(True)):
    """Run cleaning → sentiment → themes → insights sequentially."""
    results = {}
    try:
        from processing.cleaning  import run_cleaning
        from processing.sentiment import run_sentiment
        from processing.themes    import run_themes
        from agents.langgraph_pipeline import run_pipeline
        _clear_cache()
        run_cleaning()
        results["cleaning"] = "ok"
        run_sentiment(use_llm=use_llm)
        results["sentiment"] = "ok"
        run_themes(use_llm=use_llm)
        results["themes"] = "ok"
        run_pipeline()
        results["insights"] = "ok"
        return {"status": "ok", "steps": results}
    except Exception as exc:
        results["error"] = str(exc)
        raise HTTPException(500, json.dumps(results))


# ── Dev server ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=API_HOST, port=API_PORT, reload=True)
