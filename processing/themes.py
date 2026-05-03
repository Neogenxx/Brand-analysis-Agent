"""
themes.py
---------
Extracts recurring positive/negative themes and aspect-level sentiment scores
from customer reviews for each brand.

Two approaches (both run and results are merged):
  1. Keyword matching — deterministic, fast, no API key needed
  2. LLM extraction   — richer themes, requires API key
"""
import json
import re
from collections import defaultdict

import pandas as pd

from utils.config import (
    DATA_PROCESSED_PATH, BRANDS, ASPECT_KEYWORDS,
    OPENAI_API_KEY, GEMINI_API_KEY, LLM_PROVIDER, LLM_MODEL,
)
from utils.logger import get_logger

logger = get_logger("themes")


# ── Keyword-based aspect scoring ──────────────────────────────────────────────

def _aspect_score_keyword(reviews: list[str], ratings: list[float]) -> dict:
    """
    For each aspect, find reviews mentioning it and compute the average
    VADER-style sentiment (approximated by star rating → -1 to 1 scale).
    """
    scores: dict[str, dict] = {}
    for aspect, keywords in ASPECT_KEYWORDS.items():
        pattern = re.compile("|".join(keywords), re.IGNORECASE)
        aspect_ratings = [
            r for rev, r in zip(reviews, ratings) if pattern.search(rev)
        ]
        if aspect_ratings:
            avg_r = sum(aspect_ratings) / len(aspect_ratings)
            # Map 1-5 stars → 0-1 score
            scores[aspect] = {
                "score":         round((avg_r - 1) / 4, 3),
                "mention_count": len(aspect_ratings),
            }
        else:
            scores[aspect] = {"score": None, "mention_count": 0}
    return scores


# ── LLM-based theme extraction ────────────────────────────────────────────────

def _build_theme_prompt(brand: str, reviews_sample: list[str]) -> str:
    sample = "\n---\n".join(reviews_sample[:25])
    return f"""You are a product analyst for the luggage brand "{brand}".
Analyse these customer reviews from Amazon India and extract structured themes.

REVIEWS:
{sample}

Return ONLY valid JSON with exactly this structure:
{{
  "positive_themes": ["<theme1>", "<theme2>", "<theme3>", "<theme4>", "<theme5>"],
  "negative_themes": ["<theme1>", "<theme2>", "<theme3>", "<theme4>", "<theme5>"],
  "aspect_scores": {{
    "wheels":     <0.0-1.0 or null>,
    "handle":     <0.0-1.0 or null>,
    "zipper":     <0.0-1.0 or null>,
    "material":   <0.0-1.0 or null>,
    "durability": <0.0-1.0 or null>,
    "size":       <0.0-1.0 or null>,
    "weight":     <0.0-1.0 or null>
  }},
  "one_line_verdict": "<single sentence verdict for a decision-maker>"
}}

Scores: 1.0 = excellent, 0.5 = average, 0.0 = very poor.
No markdown fences. Just the JSON.
"""


def _call_llm(prompt: str) -> str:
    if LLM_PROVIDER == "gemini" and GEMINI_API_KEY:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        resp = genai.GenerativeModel("gemini-1.5-flash").generate_content(prompt)
        return resp.text.strip()
    if OPENAI_API_KEY:
        from openai import OpenAI
        resp = OpenAI(api_key=OPENAI_API_KEY).chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()
    raise RuntimeError("No LLM API key configured.")


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON. Using fallback.")
        return {}


# ── Fallback: keyword-derived themes ─────────────────────────────────────────

_GENERIC_POSITIVE = [
    "smooth wheels", "sturdy build", "spacious compartment",
    "good quality zipper", "lightweight material",
]
_GENERIC_NEGATIVE = [
    "zipper quality issues", "wheel durability concerns",
    "handle mechanism", "scratch-prone surface", "heavy when empty",
]

def _keyword_themes(brand: str, reviews_df: pd.DataFrame) -> dict:
    br = reviews_df[reviews_df["brand"] == brand]
    pos_revs = br[br["sentiment_label"] == "positive"]["body"].tolist()
    neg_revs = br[br["sentiment_label"] == "negative"]["body"].tolist()

    def _top_aspects(rev_list: list[str]) -> list[str]:
        counts: dict = defaultdict(int)
        for rev in rev_list:
            for aspect, kws in ASPECT_KEYWORDS.items():
                if any(kw.lower() in rev.lower() for kw in kws):
                    counts[aspect] += 1
        return [k for k, _ in sorted(counts.items(), key=lambda x: -x[1])][:5]

    positive_themes = [f"good {a}" for a in _top_aspects(pos_revs)] or _GENERIC_POSITIVE[:3]
    negative_themes = [f"poor {a}" for a in _top_aspects(neg_revs)] or _GENERIC_NEGATIVE[:3]

    aspect_scores = _aspect_score_keyword(
        br["body"].tolist(), br["rating"].tolist()
    )

    return {
        "positive_themes": positive_themes,
        "negative_themes": negative_themes,
        "aspect_scores":   {k: v["score"] for k, v in aspect_scores.items()},
        "aspect_mentions": {k: v["mention_count"] for k, v in aspect_scores.items()},
        "one_line_verdict": f"{brand} — keyword-derived theme analysis.",
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def run_themes(use_llm: bool = True) -> dict:
    reviews_path = DATA_PROCESSED_PATH / "reviews.csv"
    if not reviews_path.exists():
        raise FileNotFoundError("reviews.csv not found. Run cleaning first.")

    reviews_df = pd.read_csv(reviews_path)
    if "sentiment_label" not in reviews_df.columns:
        # Assign simple label from rating
        reviews_df["sentiment_label"] = reviews_df["rating"].apply(
            lambda r: "positive" if r >= 4 else ("negative" if r <= 2 else "neutral")
        )

    themes_data: dict = {}

    for brand in BRANDS:
        br = reviews_df[reviews_df["brand"] == brand]
        if br.empty:
            logger.warning(f"No reviews for {brand} — skipping themes")
            themes_data[brand] = {
                "positive_themes": [], "negative_themes": [],
                "aspect_scores": {}, "aspect_mentions": {},
                "one_line_verdict": "No data available.",
            }
            continue

        # Keyword baseline (always)
        kw_result = _keyword_themes(brand, reviews_df)

        if use_llm and (OPENAI_API_KEY or GEMINI_API_KEY):
            sample = br["body"].sample(min(25, len(br)), random_state=42).tolist()
            prompt = _build_theme_prompt(brand, sample)
            try:
                raw    = _call_llm(prompt)
                result = _parse_json(raw)
                if result:
                    # Fill in missing aspect mentions from keyword approach
                    result["aspect_mentions"] = kw_result["aspect_mentions"]
                    # Patch None aspect scores with keyword fallback
                    for asp, score in result.get("aspect_scores", {}).items():
                        if score is None:
                            result["aspect_scores"][asp] = kw_result["aspect_scores"].get(asp)
                    themes_data[brand] = result
                    logger.info(f"{brand} — LLM themes extracted")
                else:
                    themes_data[brand] = kw_result
            except Exception as exc:
                logger.error(f"LLM theme extraction failed for {brand}: {exc}")
                themes_data[brand] = kw_result
        else:
            themes_data[brand] = kw_result
            logger.info(f"{brand} — keyword themes extracted (LLM skipped)")

    out = DATA_PROCESSED_PATH / "themes.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(themes_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Themes saved → {out}")
    return themes_data


if __name__ == "__main__":
    run_themes()
