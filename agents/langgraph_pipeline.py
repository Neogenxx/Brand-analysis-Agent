"""
langgraph_pipeline.py
---------------------
5-node LangGraph reasoning pipeline for the Agent Insights section.

Node 1 — Data Aggregator   : computes per-brand metrics (pure Python)
Node 2 — Anomaly Detector  : flags contradictions  (pure Python)
Node 3 — Cross-Brand Comp  : ranks brands on key dimensions (pure Python)
Node 4 — LLM Insight Gen   : writes 5+ non-obvious conclusions (LLM)
Node 5 — Ranker + Filter   : scores and selects top 5 insights (LLM + heuristics)
"""
from __future__ import annotations

import json
import re
from typing import TypedDict, Optional

import pandas as pd

from utils.config import (
    DATA_PROCESSED_PATH, BRANDS,
    OPENAI_API_KEY, GEMINI_API_KEY, LLM_PROVIDER, LLM_MODEL,
)
from utils.logger import get_logger

logger = get_logger("agent")


# ── State schema ──────────────────────────────────────────────────────────────

class InsightState(TypedDict):
    products_csv:   str            # raw CSV string
    reviews_csv:    str            # raw CSV string
    sentiment_csv:  str            # raw CSV string
    themes_json:    str            # raw JSON string
    brand_metrics:  dict           # aggregated per-brand metrics
    anomalies:      list[dict]     # detected anomalies
    comparisons:    dict           # cross-brand comparison data
    raw_insights:   list[str]      # LLM narrative insights
    final_insights: list[dict]     # ranked & structured insight cards
    error:          Optional[str]


# ── LLM helper ────────────────────────────────────────────────────────────────

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
            temperature=0.4,
            max_tokens=2000,
        )
        return resp.choices[0].message.content.strip()
    raise RuntimeError("No LLM API key configured. Check .env.")


def _parse_json_safe(raw: str) -> list | dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


# ── Node 1: Data Aggregator ───────────────────────────────────────────────────

def node_aggregate_data(state: InsightState) -> InsightState:
    logger.info("Node 1 — Aggregating brand metrics...")
    try:
        from io import StringIO
        products_df  = pd.read_csv(StringIO(state["products_csv"]))
        sentiment_df = pd.read_csv(StringIO(state["sentiment_csv"]))

        metrics: dict = {}
        for brand in products_df["brand"].unique():
            bp = products_df[products_df["brand"] == brand]
            bs = sentiment_df[sentiment_df["brand"] == brand]

            metrics[brand] = {
                "avg_price":        round(bp["price"].mean(), 0),
                "min_price":        round(bp["price"].min(), 0),
                "max_price":        round(bp["price"].max(), 0),
                "avg_mrp":          round(bp["mrp"].mean(), 0),
                "avg_discount":     round(bp["discount_pct"].mean(), 1),
                "avg_rating":       round(bp["rating"].mean(), 2),
                "total_products":   int(len(bp)),
                "total_reviews":    int(bs["total_reviews"].sum()) if not bs.empty else 0,
                "sentiment_score":  float(bs["sentiment_score"].mean()) if not bs.empty else 50.0,
                "positive_pct":     float(bs["positive_pct"].mean())    if not bs.empty else 50.0,
                "negative_pct":     float(bs["negative_pct"].mean())    if not bs.empty else 20.0,
                "price_spread":     round(bp["price"].max() - bp["price"].min(), 0),
            }

        state["brand_metrics"] = metrics
        logger.info(f"Aggregated metrics for {len(metrics)} brands")
    except Exception as exc:
        logger.error(f"Node 1 error: {exc}")
        state["error"] = str(exc)

    return state


# ── Node 2: Anomaly Detector ──────────────────────────────────────────────────

def node_detect_anomalies(state: InsightState) -> InsightState:
    logger.info("Node 2 — Detecting anomalies...")
    anomalies: list[dict] = []
    metrics = state.get("brand_metrics", {})
    if not metrics:
        state["anomalies"] = []
        return state

    avg_disc  = sum(m["avg_discount"]    for m in metrics.values()) / len(metrics)
    avg_sent  = sum(m["sentiment_score"] for m in metrics.values()) / len(metrics)
    avg_rat   = sum(m["avg_rating"]      for m in metrics.values()) / len(metrics)

    for brand, m in metrics.items():
        # Anomaly A: high rating but low sentiment
        if m["avg_rating"] > avg_rat and m["sentiment_score"] < avg_sent - 10:
            anomalies.append({
                "type":    "rating_sentiment_gap",
                "brand":   brand,
                "detail":  (
                    f"{brand} has above-average rating ({m['avg_rating']:.1f}★) "
                    f"but below-average sentiment ({m['sentiment_score']:.0f}/100). "
                    f"Star ratings may be inflated by early or volume buyers."
                ),
                "severity": "medium",
            })

        # Anomaly B: heavy discounting + low sentiment (distress signal)
        if m["avg_discount"] > avg_disc + 8 and m["sentiment_score"] < avg_sent:
            anomalies.append({
                "type":    "discount_distress",
                "brand":   brand,
                "detail":  (
                    f"{brand} uses {m['avg_discount']:.0f}% average discount "
                    f"({m['avg_discount'] - avg_disc:.0f}% above category avg) "
                    f"while sentiment is below average ({m['sentiment_score']:.0f}/100). "
                    f"This suggests discount dependency to mask quality perception."
                ),
                "severity": "high",
            })

        # Anomaly C: wide price spread with uniform sentiment
        if m["price_spread"] > 5000:
            anomalies.append({
                "type":    "price_spread_no_quality_signal",
                "brand":   brand,
                "detail":  (
                    f"{brand} spans ₹{m['price_spread']:,.0f} in price range "
                    f"(₹{m['min_price']:,.0f}–₹{m['max_price']:,.0f}) but has "
                    f"uniform sentiment score ({m['sentiment_score']:.0f}/100). "
                    f"Buyers can't tell which price tier is 'worth it'."
                ),
                "severity": "low",
            })

        # Anomaly D: high negative % despite good overall score
        if m["negative_pct"] > 25 and m["sentiment_score"] > avg_sent:
            anomalies.append({
                "type":    "hidden_complaint_cluster",
                "brand":   brand,
                "detail":  (
                    f"{brand} shows {m['negative_pct']:.0f}% negative reviews despite "
                    f"overall sentiment of {m['sentiment_score']:.0f}/100. "
                    f"A polarised review base — loyal fans masking a significant complaint cluster."
                ),
                "severity": "medium",
            })

    state["anomalies"] = anomalies
    logger.info(f"Detected {len(anomalies)} anomalies")
    return state


# ── Node 3: Cross-Brand Comparator ────────────────────────────────────────────

def node_compare_brands(state: InsightState) -> InsightState:
    logger.info("Node 3 — Comparing brands...")
    metrics = state.get("brand_metrics", {})
    themes  = json.loads(state.get("themes_json", "{}"))

    if not metrics:
        state["comparisons"] = {}
        return state

    comparisons: dict = {}

    # Value-for-money: sentiment / avg_price (higher = better VFM)
    vfm = {b: round(m["sentiment_score"] / max(m["avg_price"], 1) * 1000, 3)
           for b, m in metrics.items()}
    comparisons["value_for_money_rank"] = sorted(vfm, key=lambda x: -vfm[x])
    comparisons["vfm_scores"] = vfm

    # Discount dependency rank (higher discount = more dependent)
    comparisons["discount_rank"] = sorted(
        metrics, key=lambda b: -metrics[b]["avg_discount"]
    )

    # Sentiment rank
    comparisons["sentiment_rank"] = sorted(
        metrics, key=lambda b: -metrics[b]["sentiment_score"]
    )

    # Premium rank (avg price)
    comparisons["price_rank"] = sorted(
        metrics, key=lambda b: -metrics[b]["avg_price"]
    )

    # Aspect leaderboard
    aspect_leader: dict[str, dict] = {}
    for asp in ["wheels", "handle", "zipper", "material", "durability", "size", "weight"]:
        scores = {
            brand: themes.get(brand, {}).get("aspect_scores", {}).get(asp)
            for brand in BRANDS
        }
        valid = {b: s for b, s in scores.items() if s is not None}
        if valid:
            best = max(valid, key=lambda b: valid[b])
            worst = min(valid, key=lambda b: valid[b])
            aspect_leader[asp] = {
                "best":        best,
                "best_score":  valid[best],
                "worst":       worst,
                "worst_score": valid[worst],
                "all_scores":  valid,
            }
    comparisons["aspect_leaderboard"] = aspect_leader

    state["comparisons"] = comparisons
    logger.info("Cross-brand comparison complete")
    return state


# ── Node 4: LLM Insight Generator ────────────────────────────────────────────

def _build_insight_prompt(
    metrics: dict, anomalies: list, comparisons: dict, themes: dict
) -> str:
    metrics_str    = json.dumps(metrics,     indent=2)
    anomalies_str  = json.dumps(anomalies,   indent=2)
    comparison_str = json.dumps(comparisons, indent=2)

    # Compact theme summary
    theme_lines = []
    for brand, t in themes.items():
        pos = ", ".join(t.get("positive_themes", [])[:3])
        neg = ", ".join(t.get("negative_themes", [])[:3])
        theme_lines.append(f"{brand}: Pros=[{pos}], Cons=[{neg}]")
    theme_str = "\n".join(theme_lines)

    return f"""You are a senior competitive intelligence analyst for the Indian luggage market.

You have been given structured data from Amazon India for these luggage brands:
Safari, Skybags, American Tourister, VIP, Aristocrat, Nasher Miles.

BRAND METRICS:
{metrics_str}

DETECTED ANOMALIES:
{anomalies_str}

CROSS-BRAND COMPARISONS:
{comparison_str}

THEME SUMMARY (Pros / Cons):
{theme_str}

Your task: Write EXACTLY 6 non-obvious, decision-ready insights. Each insight must:
- Go beyond simply reporting a number
- Explain WHY something is happening or what it means strategically
- Be specific (name brands, cite data points)
- Be useful to a brand manager or investor

Return a JSON array of 6 objects:
[
  {{
    "title": "<punchy 8-12 word title>",
    "body": "<2-3 sentence explanation with specific data points>",
    "brands": ["<brand1>", "<brand2>"],
    "category": "<one of: Pricing Strategy | Value-for-Money | Product Quality | Competitive Position | Anomaly | Risk>",
    "confidence": "<High | Medium | Low>",
    "evidence": "<one-line data reference>"
  }},
  ...
]

No markdown. Only the JSON array.
"""


def node_generate_insights(state: InsightState) -> InsightState:
    logger.info("Node 4 — Generating LLM insights...")
    metrics     = state.get("brand_metrics", {})
    anomalies   = state.get("anomalies", [])
    comparisons = state.get("comparisons", {})
    themes      = json.loads(state.get("themes_json", "{}"))

    if not metrics:
        logger.warning("No metrics available — skipping LLM insights")
        state["raw_insights"] = []
        return state

    prompt = _build_insight_prompt(metrics, anomalies, comparisons, themes)

    try:
        raw = _call_llm(prompt)
        parsed = _parse_json_safe(raw)
        if isinstance(parsed, list):
            state["raw_insights"] = parsed
            logger.info(f"LLM generated {len(parsed)} raw insights")
        else:
            logger.warning("LLM did not return a list — using empty")
            state["raw_insights"] = []
    except Exception as exc:
        logger.error(f"Node 4 LLM error: {exc}")
        state["raw_insights"] = []
        state["error"] = str(exc)

    return state


# ── Node 5: Ranker + Filter ───────────────────────────────────────────────────

def _score_insight(insight: dict, idx: int) -> float:
    """
    Heuristic scoring for novelty + decision impact.
    Higher = more valuable.
    """
    score = 0.0

    # Confidence bonus
    conf_map = {"High": 3.0, "Medium": 1.5, "Low": 0.5}
    score += conf_map.get(insight.get("confidence", "Low"), 0)

    # Category bonus (anomalies and risks are most interesting)
    cat_map = {
        "Anomaly": 2.0, "Risk": 2.0, "Competitive Position": 1.5,
        "Value-for-Money": 1.3, "Pricing Strategy": 1.2, "Product Quality": 1.0,
    }
    score += cat_map.get(insight.get("category", ""), 1.0)

    # Multi-brand penalty (single-brand insights are more specific)
    brands = insight.get("brands", [])
    if len(brands) == 1:
        score += 0.5

    # Body length bonus (longer = more evidence)
    body_len = len(insight.get("body", ""))
    score += min(body_len / 400, 1.0)

    # Slight penalty for early position (LLM tends to put obvious ones first)
    score -= idx * 0.1

    return round(score, 3)


def node_rank_filter(state: InsightState) -> InsightState:
    logger.info("Node 5 — Ranking and filtering insights...")
    raw = state.get("raw_insights", [])

    if not raw:
        # Fallback: use anomalies as insights
        anomaly_insights = [
            {
                "rank":       i + 1,
                "title":      a["type"].replace("_", " ").title(),
                "body":       a["detail"],
                "brands":     [a["brand"]],
                "category":   "Anomaly",
                "confidence": "Medium" if a["severity"] == "medium" else "High",
                "evidence":   f"Anomaly type: {a['type']}",
            }
            for i, a in enumerate(state.get("anomalies", [])[:5])
        ]
        state["final_insights"] = anomaly_insights
        return state

    # Score each
    scored = [(ins, _score_insight(ins, i)) for i, ins in enumerate(raw)]
    scored.sort(key=lambda x: -x[1])

    # Deduplicate by title similarity (simple)
    seen_titles: set[str] = set()
    final: list[dict] = []
    for ins, score in scored:
        title_key = ins.get("title", "")[:30].lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        ins["rank"] = len(final) + 1
        ins["score"] = score
        final.append(ins)
        if len(final) >= 5:
            break

    state["final_insights"] = final
    logger.info(f"Final insights: {len(final)} selected")
    return state


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_graph():
    from langgraph.graph import StateGraph, END

    builder = StateGraph(InsightState)
    builder.add_node("aggregate",        node_aggregate_data)
    builder.add_node("detect_anomalies", node_detect_anomalies)
    builder.add_node("compare_brands",   node_compare_brands)
    builder.add_node("generate_insights",node_generate_insights)
    builder.add_node("rank_filter",      node_rank_filter)

    builder.set_entry_point("aggregate")
    builder.add_edge("aggregate",         "detect_anomalies")
    builder.add_edge("detect_anomalies",  "compare_brands")
    builder.add_edge("compare_brands",    "generate_insights")
    builder.add_edge("generate_insights", "rank_filter")
    builder.add_edge("rank_filter",       END)

    return builder.compile()


# ── Main entry point ──────────────────────────────────────────────────────────

def run_pipeline() -> list[dict]:
    """
    Load processed data, run LangGraph pipeline, save insights.json.
    Returns the final list of insight cards.
    """
    # Load files
    def _read(filename: str) -> str:
        path = DATA_PROCESSED_PATH / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        logger.warning(f"{filename} not found — using empty string")
        return ""

    initial_state: InsightState = {
        "products_csv":   _read("products.csv"),
        "reviews_csv":    _read("reviews.csv"),
        "sentiment_csv":  _read("sentiment.csv"),
        "themes_json":    _read("themes.json"),
        "brand_metrics":  {},
        "anomalies":      [],
        "comparisons":    {},
        "raw_insights":   [],
        "final_insights": [],
        "error":          None,
    }

    try:
        graph = build_graph()
        result = graph.invoke(initial_state)
    except ImportError:
        # LangGraph not installed — run nodes sequentially
        logger.warning("LangGraph not available — running nodes sequentially")
        result = node_aggregate_data(initial_state)
        result = node_detect_anomalies(result)
        result = node_compare_brands(result)
        result = node_generate_insights(result)
        result = node_rank_filter(result)

    final = result.get("final_insights", [])

    out = DATA_PROCESSED_PATH / "insights.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)
    logger.info(f"Insights saved → {out} ({len(final)} insights)")

    return final


if __name__ == "__main__":
    insights = run_pipeline()
    for ins in insights:
        print(f"\n[{ins.get('rank', '?')}] {ins.get('title', '')}")
        print(f"    {ins.get('body', '')[:120]}...")
