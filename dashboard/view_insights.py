"""
view_insights.py  —  Dashboard Tab 4: Agent Insights
The highest-value section. Auto-generated non-obvious conclusions from the LangGraph pipeline.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from dashboard.data_loader import (
    load_insights, get_brand_summary, load_themes,
    clear_all_cache,
)
from dashboard.charts import BRAND_COLORS, CONFIDENCE_COLORS

CATEGORY_ICONS = {
    "Pricing Strategy":      "💰",
    "Value-for-Money":       "🏆",
    "Product Quality":       "🔧",
    "Competitive Position":  "⚔️",
    "Anomaly":               "⚠️",
    "Risk":                  "🚨",
    "Anomaly Detection":     "⚠️",
    "Product Quality Risk":  "🚨",
}

CATEGORY_COLORS_MAP = {
    "Pricing Strategy":      "#4F8EF7",
    "Value-for-Money":       "#43D39E",
    "Product Quality":       "#A78BFA",
    "Competitive Position":  "#FB923C",
    "Anomaly":               "#F7B731",
    "Risk":                  "#F76C6C",
    "Anomaly Detection":     "#F7B731",
    "Product Quality Risk":  "#F76C6C",
}


def _insight_card(ins: dict):
    rank      = ins.get("rank", "?")
    title     = ins.get("title", "Unnamed Insight")
    body      = ins.get("body", "")
    brands    = ins.get("brands", [])
    category  = ins.get("category", "Insight")
    confidence= ins.get("confidence", "Medium")
    evidence  = ins.get("evidence", "")

    cat_color  = CATEGORY_COLORS_MAP.get(category, "#94A3B8")
    conf_color = CONFIDENCE_COLORS.get(confidence, "#94A3B8")
    icon       = CATEGORY_ICONS.get(category, "💡")

    brand_chips = "".join(
        f"<span style='background:{BRAND_COLORS.get(b, '#334155')}22;"
        f"color:{BRAND_COLORS.get(b, '#94A3B8')};border:1px solid "
        f"{BRAND_COLORS.get(b, '#334155')}55;border-radius:12px;"
        f"padding:2px 9px;font-size:11px;margin-right:4px'>{b}</span>"
        for b in brands
    )

    st.markdown(
        f"""
        <div style="background:#0F172A;border:1px solid #1E293B;
                    border-left:4px solid {cat_color};
                    border-radius:0 12px 12px 0;
                    padding:20px 22px;margin-bottom:18px;">

          <!-- Header row -->
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;
                      flex-wrap:wrap">
            <span style="background:{cat_color}22;color:{cat_color};
                         border:1px solid {cat_color}55;border-radius:6px;
                         padding:3px 10px;font-size:12px;font-weight:600">
              {icon} {category}
            </span>
            <span style="background:{conf_color}22;color:{conf_color};
                         border:1px solid {conf_color}55;border-radius:6px;
                         padding:3px 10px;font-size:11px;">
              {confidence} confidence
            </span>
            <span style="color:#475569;font-size:13px;margin-left:auto">
              #{rank}
            </span>
          </div>

          <!-- Title -->
          <div style="color:#F8FAFC;font-size:17px;font-weight:700;
                      margin-bottom:10px;line-height:1.4">
            {title}
          </div>

          <!-- Body -->
          <div style="color:#CBD5E1;font-size:13px;line-height:1.7;
                      margin-bottom:14px">
            {body}
          </div>

          <!-- Brand chips -->
          <div style="margin-bottom:10px">{brand_chips}</div>

          <!-- Evidence -->
          {"<div style='background:#0D1A2B;border-radius:6px;padding:8px 12px;" +
           "font-size:11px;color:#64748B;font-family:monospace'>📎 " +
           evidence + "</div>" if evidence else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _anomaly_radar(summary: pd.DataFrame):
    """Mini radar comparing top vs bottom brand on key dimensions."""
    if summary.empty or len(summary) < 2:
        return

    dims = ["avg_price", "avg_discount", "avg_rating", "sentiment_score",
            "positive_pct", "value_score"]
    labels = ["Price", "Discount", "Rating", "Sentiment", "Positive%", "VFM"]

    fig = go.Figure()

    # Normalise to 0-1 for each dim
    norm = summary.copy()
    for d in dims:
        col = norm[d]
        mn, mx = col.min(), col.max()
        norm[d] = (col - mn) / (mx - mn + 1e-9)

    top   = summary.loc[summary["sentiment_score"].idxmax()]
    worst = summary.loc[summary["sentiment_score"].idxmin()]

    for row, norm_row, style in [(top, norm[norm["brand"]==top["brand"]].iloc[0], "solid"),
                                  (worst, norm[norm["brand"]==worst["brand"]].iloc[0], "dot")]:
        brand  = row["brand"]
        values = [float(norm_row[d]) for d in dims]
        values_c = values + [values[0]]
        fig.add_trace(go.Scatterpolar(
            r=values_c,
            theta=labels + [labels[0]],
            fill="toself",
            fillcolor=BRAND_COLORS.get(brand, "#94A3B8"),
            opacity=0.2,
            line=dict(color=BRAND_COLORS.get(brand, "#94A3B8"), width=2, dash=style),
            name=brand,
        ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor ="rgba(0,0,0,0)",
        font=dict(color="#CBD5E1", size=11),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 1], gridcolor="#1E293B",
                            tickfont=dict(color="#475569")),
            angularaxis=dict(gridcolor="#1E293B", tickfont=dict(color="#CBD5E1")),
        ),
        title=dict(text="Best vs Worst — normalised across all dimensions",
                   font=dict(color="#CBD5E1")),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#CBD5E1")),
        margin=dict(l=30, r=30, t=50, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_insights(selected_brands: list[str]):
    st.markdown("## 🤖 Agent Insights")
    st.markdown(
        "<p style='color:#94A3B8;font-size:14px'>"
        "Auto-generated non-obvious conclusions by the LangGraph reasoning pipeline. "
        "These go beyond charts — they explain <em>why</em> something is happening "
        "and what a decision-maker should do next."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Refresh button ────────────────────────────────────────────────────────
    col_refresh, col_note = st.columns([1, 4])
    with col_refresh:
        if st.button("🔄 Regenerate Insights", use_container_width=True):
            with st.spinner("Running LangGraph pipeline..."):
                try:
                    from agents.langgraph_pipeline import run_pipeline
                    clear_all_cache()
                    run_pipeline()
                    st.success("Insights refreshed!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Pipeline error: {e}")
    with col_note:
        st.caption(
            "Insights are generated from your cleaned dataset using the 5-node LangGraph pipeline. "
            "Requires API key for LLM-powered insights; otherwise uses deterministic logic."
        )

    insights = load_insights()

    if not insights:
        st.warning(
            "No insights generated yet. Click **Regenerate Insights** above, "
            "or ensure data/processed/insights.json exists."
        )
        _show_fallback_insights(selected_brands)
        return

    # ── Category filter ───────────────────────────────────────────────────────
    all_cats = sorted({ins.get("category", "Insight") for ins in insights})
    selected_cats = st.multiselect(
        "Filter by category", all_cats, default=all_cats,
    )
    filtered_insights = [
        ins for ins in insights
        if ins.get("category", "Insight") in selected_cats
    ]

    # ── Insight cards ─────────────────────────────────────────────────────────
    st.markdown(f"**{len(filtered_insights)} insights** | ranked by novelty and decision impact")
    st.markdown("<br>", unsafe_allow_html=True)

    for ins in filtered_insights:
        _insight_card(ins)

    # ── Best vs Worst radar ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Best vs worst performer — normalised radar")
    summary = get_brand_summary()
    if not summary.empty:
        summary = summary[summary["brand"].isin(selected_brands)]
        _anomaly_radar(summary)

    # ── Summary stats of insights ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Insight breakdown")

    insight_df = pd.DataFrame(insights)
    if not insight_df.empty and "category" in insight_df.columns:
        cat_counts = insight_df["category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Count"]

        conf_counts = insight_df["confidence"].value_counts().reset_index()
        conf_counts.columns = ["Confidence", "Count"]

        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown("**By category**")
            st.dataframe(cat_counts, use_container_width=True, hide_index=True)
        with cc2:
            st.markdown("**By confidence**")
            st.dataframe(conf_counts, use_container_width=True, hide_index=True)


def _show_fallback_insights(selected_brands: list[str]):
    """Show deterministic insights from summary data when LLM insights unavailable."""
    st.markdown("---")
    st.markdown("### Deterministic insights (no LLM required)")

    summary = get_brand_summary()
    if summary.empty:
        return

    summary = summary[summary["brand"].isin(selected_brands)]

    # Most discount-dependent
    max_disc = summary.loc[summary["avg_discount"].idxmax()]
    _insight_card({
        "rank": 1,
        "title": f"{max_disc['brand']} is the most discount-dependent brand",
        "body": (
            f"{max_disc['brand']} averages {max_disc['avg_discount']:.1f}% discount — "
            f"the highest in the category. This may indicate difficulty sustaining demand "
            f"at listed prices, or a deliberate volume-over-margin strategy."
        ),
        "brands": [max_disc["brand"]],
        "category": "Pricing Strategy",
        "confidence": "High",
        "evidence": f"Avg discount: {max_disc['avg_discount']:.1f}% | Sentiment: {max_disc['sentiment_score']:.0f}/100",
    })

    # Value-for-money leader
    best_vfm = summary.loc[summary["value_score"].idxmax()]
    _insight_card({
        "rank": 2,
        "title": f"{best_vfm['brand']} delivers the best value-for-money",
        "body": (
            f"{best_vfm['brand']} achieves the best sentiment-to-price ratio in the category "
            f"with a VFM score of {best_vfm['value_score']:.2f}. "
            f"At ₹{best_vfm['avg_price']:,.0f} average price and {best_vfm['sentiment_score']:.0f}/100 sentiment, "
            f"it outperforms rivals for cost-conscious buyers."
        ),
        "brands": [best_vfm["brand"]],
        "category": "Value-for-Money",
        "confidence": "High",
        "evidence": f"VFM score: {best_vfm['value_score']:.3f} | Avg price: ₹{best_vfm['avg_price']:,.0f}",
    })

    # Premium leader
    premium = summary.loc[summary["avg_price"].idxmax()]
    _insight_card({
        "rank": 3,
        "title": f"{premium['brand']} holds the premium position in the category",
        "body": (
            f"{premium['brand']} has the highest average price of ₹{premium['avg_price']:,.0f}. "
            f"With a sentiment score of {premium['sentiment_score']:.0f}/100, it "
            + ("justifies its premium through quality perception." if premium["sentiment_score"] > 65
               else "struggles to justify its premium on sentiment alone.")
        ),
        "brands": [premium["brand"]],
        "category": "Competitive Position",
        "confidence": "High",
        "evidence": f"Avg price: ₹{premium['avg_price']:,.0f} | Sentiment: {premium['sentiment_score']:.0f}/100",
    })
