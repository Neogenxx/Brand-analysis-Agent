"""
sentiment.py
------------
Two-layer sentiment pipeline:
  Layer 1 — VADER: fast per-review polarity scoring (no API calls needed)
  Layer 2 — LLM  : brand-level narrative summary and sentiment score
Output: data/processed/sentiment.csv
"""
import json
import os
from pathlib import Path

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from utils.config import (
    DATA_PROCESSED_PATH, BRANDS,
    OPENAI_API_KEY, GEMINI_API_KEY, LLM_PROVIDER, LLM_MODEL,
)
from utils.logger import get_logger

logger = get_logger("sentiment")

analyzer = SentimentIntensityAnalyzer()


# ── VADER per-review ──────────────────────────────────────────────────────────

def _vader_score(text: str) -> dict:
    scores = analyzer.polarity_scores(text)
    label = (
        "positive" if scores["compound"] >= 0.05
        else "negative" if scores["compound"] <= -0.05
        else "neutral"
    )
    return {
        "sentiment_score": round(scores["compound"], 4),
        "sentiment_label": label,
        "pos": round(scores["pos"], 4),
        "neg": round(scores["neg"], 4),
        "neu": round(scores["neu"], 4),
    }


def score_reviews(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """Add VADER sentiment columns to reviews DataFrame."""
    logger.info("Running VADER sentiment on reviews...")
    vader_cols = reviews_df["body"].apply(lambda t: pd.Series(_vader_score(str(t))))
    return pd.concat([reviews_df, vader_cols], axis=1)


# ── LLM brand-level summary ───────────────────────────────────────────────────

def _build_prompt(brand: str, reviews_sample: list[str]) -> str:
    sample_text = "\n---\n".join(reviews_sample[:30])
    return f"""You are a competitive intelligence analyst reviewing customer feedback for the luggage brand "{brand}" on Amazon India.

Below are up to 30 customer reviews:
{sample_text}

Return ONLY a valid JSON object with exactly these keys:
{{
  "sentiment_score": <integer 0-100, overall positive sentiment>,
  "summary": "<2-3 sentence summary of customer sentiment>",
  "top_positives": ["<theme1>", "<theme2>", "<theme3>"],
  "top_negatives": ["<theme1>", "<theme2>", "<theme3>"]
}}

No markdown, no explanation — just the JSON object.
"""


def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()


def _call_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    resp  = model.generate_content(prompt)
    return resp.text.strip()


def _call_llm(prompt: str) -> str:
    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        return _call_gemini(prompt)
    if OPENAI_API_KEY:
        return _call_openai(prompt)
    raise RuntimeError(
        "No LLM API key configured. Set OPENAI_API_KEY or GEMINI_API_KEY in .env"
    )


def _parse_llm_response(raw: str) -> dict:
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def brand_sentiment_llm(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """LLM-powered brand-level sentiment summaries."""
    rows = []
    for brand in BRANDS:
        br = reviews_df[reviews_df["brand"] == brand]
        if br.empty:
            logger.warning(f"No reviews for {brand} — using VADER only")
            rows.append({"brand": brand, "llm_sentiment_score": None, "llm_summary": "", "llm_top_positives": [], "llm_top_negatives": []})
            continue

        sample = br["body"].sample(min(30, len(br)), random_state=42).tolist()
        prompt = _build_prompt(brand, sample)

        try:
            raw  = _call_llm(prompt)
            data = _parse_llm_response(raw)
            rows.append({
                "brand":               brand,
                "llm_sentiment_score": data.get("sentiment_score"),
                "llm_summary":         data.get("summary", ""),
                "llm_top_positives":   data.get("top_positives", []),
                "llm_top_negatives":   data.get("top_negatives", []),
            })
            logger.info(f"{brand} — LLM sentiment: {data.get('sentiment_score')}/100")
        except Exception as exc:
            logger.error(f"LLM call failed for {brand}: {exc}")
            rows.append({"brand": brand, "llm_sentiment_score": None, "llm_summary": "", "llm_top_positives": [], "llm_top_negatives": []})

    return pd.DataFrame(rows)


# ── Aggregate ─────────────────────────────────────────────────────────────────

def aggregate_brand_sentiment(reviews_df: pd.DataFrame, llm_df: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    for brand in BRANDS:
        br = reviews_df[reviews_df["brand"] == brand]
        if br.empty:
            continue

        pos_pct = (br["sentiment_label"] == "positive").mean() * 100
        neg_pct = (br["sentiment_label"] == "negative").mean() * 100
        neu_pct = (br["sentiment_label"] == "neutral").mean()  * 100
        # VADER compound averages to a 0-100 scale
        vader_score = round((br["sentiment_score"].mean() + 1) / 2 * 100, 1)

        row = {
            "brand":             brand,
            "sentiment_score":   vader_score,
            "positive_pct":      round(pos_pct, 1),
            "negative_pct":      round(neg_pct, 1),
            "neutral_pct":       round(neu_pct, 1),
            "avg_review_rating": round(br["rating"].mean(), 2),
            "total_reviews":     len(br),
            "llm_sentiment_score": None,
            "llm_summary":        "",
            "llm_top_positives":  "[]",
            "llm_top_negatives":  "[]",
        }

        # Merge LLM data if available
        if llm_df is not None and not llm_df.empty:
            lrow = llm_df[llm_df["brand"] == brand]
            if not lrow.empty:
                lrow = lrow.iloc[0]
                # Blend: 60% VADER + 40% LLM if LLM score exists
                llm_s = lrow.get("llm_sentiment_score")
                if llm_s is not None:
                    row["sentiment_score"]     = round(vader_score * 0.6 + llm_s * 0.4, 1)
                    row["llm_sentiment_score"] = llm_s
                row["llm_summary"]       = lrow.get("llm_summary", "")
                row["llm_top_positives"] = json.dumps(lrow.get("llm_top_positives", []))
                row["llm_top_negatives"] = json.dumps(lrow.get("llm_top_negatives", []))

        rows.append(row)

    return pd.DataFrame(rows)


# ── Main ──────────────────────────────────────────────────────────────────────

def run_sentiment(use_llm: bool = True) -> pd.DataFrame:
    reviews_path = DATA_PROCESSED_PATH / "reviews.csv"
    if not reviews_path.exists():
        raise FileNotFoundError("reviews.csv not found. Run cleaning first.")

    reviews_df = pd.read_csv(reviews_path)
    logger.info(f"Loaded {len(reviews_df)} reviews")

    # Layer 1: VADER
    reviews_df = score_reviews(reviews_df)
    reviews_df.to_csv(DATA_PROCESSED_PATH / "reviews.csv", index=False)

    # Layer 2: LLM (optional — requires API key)
    llm_df = None
    if use_llm and (OPENAI_API_KEY or GEMINI_API_KEY):
        logger.info("Running LLM brand-level sentiment...")
        llm_df = brand_sentiment_llm(reviews_df)
    else:
        logger.info("LLM skipped — using VADER only for brand aggregation")

    sentiment_df = aggregate_brand_sentiment(reviews_df, llm_df)
    sentiment_df.to_csv(DATA_PROCESSED_PATH / "sentiment.csv", index=False)
    logger.info(f"Sentiment saved → {DATA_PROCESSED_PATH / 'sentiment.csv'}")

    return sentiment_df


if __name__ == "__main__":
    run_sentiment()
