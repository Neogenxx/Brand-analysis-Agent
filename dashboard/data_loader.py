"""
data_loader.py
--------------
Centralised data access layer for the Streamlit dashboard.
Reads from data/processed/ and caches everything in st.cache_data.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.config import DATA_PROCESSED_PATH, BRANDS
from utils.logger import get_logger

logger = get_logger("dashboard.loader")


# ── Cached loaders ────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_products() -> pd.DataFrame:
    path = DATA_PROCESSED_PATH / "products.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    # Ensure numeric
    for col in ["price", "mrp", "discount_pct", "rating", "review_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_reviews() -> pd.DataFrame:
    path = DATA_PROCESSED_PATH / "reviews.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    for col in ["rating", "sentiment_score"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_sentiment() -> pd.DataFrame:
    path = DATA_PROCESSED_PATH / "sentiment.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    for col in ["sentiment_score", "positive_pct", "negative_pct", "neutral_pct",
                "avg_review_rating", "total_reviews"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=300)
def load_themes() -> dict:
    path = DATA_PROCESSED_PATH / "themes.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(ttl=300)
def load_insights() -> list[dict]:
    path = DATA_PROCESSED_PATH / "insights.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clear_all_cache():
    st.cache_data.clear()


# ── Derived / merged frames ───────────────────────────────────────────────────

def get_brand_summary() -> pd.DataFrame:
    """Returns one row per brand with all key metrics merged."""
    products_df  = load_products()
    sentiment_df = load_sentiment()
    themes       = load_themes()

    if products_df.empty:
        return pd.DataFrame()

    prod_agg = products_df.groupby("brand").agg(
        avg_price       =("price",        "mean"),
        min_price       =("price",        "min"),
        max_price       =("price",        "max"),
        avg_discount    =("discount_pct", "mean"),
        avg_rating      =("rating",       "mean"),
        total_products  =("asin",         "count"),
        total_reviews   =("review_count", "sum"),
    ).reset_index()

    prod_agg["avg_price"]    = prod_agg["avg_price"].round(0)
    prod_agg["avg_discount"] = prod_agg["avg_discount"].round(1)
    prod_agg["avg_rating"]   = prod_agg["avg_rating"].round(2)

    if not sentiment_df.empty:
        sent_agg = sentiment_df.groupby("brand").agg(
            sentiment_score=("sentiment_score", "mean"),
            positive_pct   =("positive_pct",    "mean"),
            negative_pct   =("negative_pct",    "mean"),
        ).reset_index()
        df = prod_agg.merge(sent_agg, on="brand", how="left")
    else:
        df = prod_agg
        df["sentiment_score"] = 50.0
        df["positive_pct"]    = 50.0
        df["negative_pct"]    = 20.0

    # Value-for-money score
    df["value_score"] = (
        df["sentiment_score"] / df["avg_price"].clip(lower=1) * 1000
    ).round(3)

    # Aspect scores from themes
    for asp in ["wheels", "handle", "zipper", "material", "durability", "size", "weight"]:
        df[f"{asp}_score"] = df["brand"].map(
            lambda b, a=asp: themes.get(b, {}).get("aspect_scores", {}).get(a)
        )

    # Positioning label
    price_median = df["avg_price"].median()
    df["positioning"] = df["avg_price"].apply(
        lambda p: "Premium" if p > price_median * 1.2
        else ("Value" if p < price_median * 0.8 else "Mid-Market")
    )

    return df


def get_available_brands() -> list[str]:
    df = load_products()
    if df.empty:
        return BRANDS
    return sorted(df["brand"].unique().tolist())


def data_is_ready() -> bool:
    return (DATA_PROCESSED_PATH / "products.csv").exists()
