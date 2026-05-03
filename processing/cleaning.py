"""
cleaning.py
-----------
Loads raw JSON files from data/raw/, normalises all fields,
and saves cleaned CSV files to data/processed/.
"""
import json
import re
from pathlib import Path

import pandas as pd
import numpy as np

from utils.config import DATA_RAW_PATH, DATA_PROCESSED_PATH, BRANDS
from utils.logger import get_logger

logger = get_logger("cleaning")


# ── Normalisation helpers ─────────────────────────────────────────────────────

def _clean_price(val) -> float:
    if pd.isna(val) or val == 0:
        return 0.0
    text = re.sub(r"[₹,\s\u20b9]", "", str(val))
    try:
        return round(float(text), 2)
    except ValueError:
        return 0.0


def _clean_rating(val) -> float:
    if pd.isna(val):
        return 0.0
    try:
        f = float(str(val).split()[0])
        return round(min(5.0, max(0.0, f)), 1)
    except (ValueError, IndexError):
        return 0.0


def _clean_discount(price: float, mrp: float, raw_disc) -> float:
    if raw_disc and float(raw_disc) > 0:
        return round(float(raw_disc), 1)
    if mrp > price > 0:
        return round((1 - price / mrp) * 100, 1)
    return 0.0


def _size_category(title: str) -> str:
    title_lower = title.lower()
    if any(x in title_lower for x in ["55cm", "55 cm", "cabin", "carry-on", "carry on"]):
        return "Cabin (≤55cm)"
    if any(x in title_lower for x in ["77cm", "79cm", "large", "xl"]):
        return "Large (≥77cm)"
    return "Medium (65–68cm)"


def _clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Remove HTML tags, extra whitespace
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ── Products pipeline ─────────────────────────────────────────────────────────

def clean_products(raw_data: dict) -> pd.DataFrame:
    rows = []
    for brand, data in raw_data.items():
        for p in data.get("products", []):
            price = _clean_price(p.get("price", 0))
            mrp   = _clean_price(p.get("mrp", 0))
            if mrp < price:
                mrp = price
            disc  = _clean_discount(price, mrp, p.get("discount_pct", 0))
            rows.append({
                "asin":          p.get("asin", ""),
                "brand":         brand,
                "title":         _clean_text(p.get("title", "")),
                "url":           p.get("url", ""),
                "price":         price,
                "mrp":           mrp,
                "discount_pct":  disc,
                "rating":        _clean_rating(p.get("rating", 0)),
                "review_count":  int(p.get("review_count", 0)),
                "size_category": _size_category(p.get("title", "")),
            })

    if not rows:
        logger.warning("No product rows found in raw data.")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Drop duplicates by ASIN
    df = df.drop_duplicates(subset=["asin"]).reset_index(drop=True)
    # Drop rows with zero price
    df = df[df["price"] > 0].reset_index(drop=True)

    logger.info(f"Cleaned products: {len(df)} rows across {df['brand'].nunique()} brands")
    return df


# ── Reviews pipeline ──────────────────────────────────────────────────────────

def clean_reviews(raw_data: dict) -> pd.DataFrame:
    rows = []
    for brand, data in raw_data.items():
        for r in data.get("reviews", []):
            body = _clean_text(r.get("body", ""))
            if len(body) < 10:          # skip very short / empty reviews
                continue
            rows.append({
                "asin":          r.get("asin", ""),
                "brand":         brand,
                "product_title": _clean_text(r.get("product_title", "")),
                "title":         _clean_text(r.get("title", "")),
                "body":          body,
                "rating":        _clean_rating(r.get("rating", 0)),
                "date":          r.get("date", ""),
                "verified":      bool(r.get("verified", False)),
            })

    if not rows:
        logger.warning("No review rows found in raw data.")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # Deduplicate by (asin + first 100 chars of body)
    df["_key"] = df["asin"] + df["body"].str[:100]
    df = df.drop_duplicates(subset=["_key"]).drop(columns=["_key"]).reset_index(drop=True)

    logger.info(f"Cleaned reviews: {len(df)} rows across {df['brand'].nunique()} brands")
    return df


# ── Main ──────────────────────────────────────────────────────────────────────

def run_cleaning() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load all raw brand JSONs, clean, and save processed CSVs."""
    raw_data: dict = {}

    for brand in BRANDS:
        fname = DATA_RAW_PATH / f"{brand.lower().replace(' ', '_')}.json"
        if fname.exists():
            with open(fname, encoding="utf-8") as f:
                raw_data[brand] = json.load(f)
            logger.info(f"Loaded {fname.name}")
        else:
            logger.warning(f"Raw file not found for {brand}: {fname}")

    if not raw_data:
        raise FileNotFoundError(
            "No raw data files found. Run the scraper first or generate sample data."
        )

    products_df = clean_products(raw_data)
    reviews_df  = clean_reviews(raw_data)

    DATA_PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    products_df.to_csv(DATA_PROCESSED_PATH / "products.csv", index=False)
    reviews_df.to_csv(DATA_PROCESSED_PATH  / "reviews.csv",  index=False)

    logger.info(f"Products saved → {DATA_PROCESSED_PATH / 'products.csv'}")
    logger.info(f"Reviews  saved → {DATA_PROCESSED_PATH / 'reviews.csv'}")

    return products_df, reviews_df


if __name__ == "__main__":
    run_cleaning()
