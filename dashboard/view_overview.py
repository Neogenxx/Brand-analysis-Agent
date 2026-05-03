"""
view_overview.py  —  Dashboard Tab 1: Overview
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from dashboard.data_loader import (
    load_products, load_reviews, load_sentiment, get_brand_summary,
)
from dashboard.charts import (
    bar_avg_price, bar_sentiment, scatter_price_vs_sentiment,
    stacked_sentiment, bar_value_for_money, BRAND_COLORS,
)


# ── KPI metric card ───────────────────────────────────────────────────────────

def _kpi(col, label: str, value: str, delta: str | None = None, icon: str = ""):
    with col:
        st.markdown(
            f"""
            <div style="background:#0F172A;border:1px solid #1E293B;border-radius:12px;
                        padding:20px 18px;text-align:center;">
              <div style="font-size:26px;margin-bottom:4px;">{icon}</div>
              <div style="font-size:28px;font-weight:700;color:#F8FAFC;">{value}</div>
              <div style="font-size:12px;color:#94A3B8;margin-top:4px;">{label}</div>
              {"<div style='font-size:11px;color:#43D39E;margin-top:2px;'>" + delta + "</div>" if delta else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_overview(selected_brands: list[str]):
    st.markdown("## 📊 Dashboard Overview")
    st.caption("Real-time snapshot of all tracked brands on Amazon India")

    products_df  = load_products()
    reviews_df   = load_reviews()
    sentiment_df = load_sentiment()

    # Filter to selected brands
    if not products_df.empty:
        products_df  = products_df[products_df["brand"].isin(selected_brands)]
    if not reviews_df.empty:
        reviews_df   = reviews_df[reviews_df["brand"].isin(selected_brands)]
    if not sentiment_df.empty:
        sentiment_df = sentiment_df[sentiment_df["brand"].isin(selected_brands)]

    # ── KPI Row ───────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    _kpi(c1, "Brands Tracked",    str(len(selected_brands)),                                 icon="🏷️")
    _kpi(c2, "Products Analysed", f"{len(products_df):,}"  if not products_df.empty else "–", icon="🧳")
    _kpi(c3, "Reviews Processed", f"{len(reviews_df):,}"   if not reviews_df.empty else "–", icon="💬")

    if not sentiment_df.empty:
        avg_sent = sentiment_df["sentiment_score"].mean()
        _kpi(c4, "Avg Sentiment",  f"{avg_sent:.0f}/100", icon="😊")
    else:
        _kpi(c4, "Avg Sentiment",  "–", icon="😊")

    if not products_df.empty:
        avg_disc = products_df["discount_pct"].mean()
        _kpi(c5, "Avg Discount",   f"{avg_disc:.1f}%", icon="🏷️")
    else:
        _kpi(c5, "Avg Discount", "–", icon="🏷️")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Summary table ──────────────────────────────────────────────────────────
    summary = get_brand_summary()
    if not summary.empty:
        summary = summary[summary["brand"].isin(selected_brands)]

    if summary.empty:
        st.info("No data yet. Use the sidebar to generate sample data or run the scraper.")
        return

    st.markdown("### Brand snapshot")
    display_cols = {
        "brand":          "Brand",
        "avg_price":      "Avg Price (₹)",
        "avg_discount":   "Avg Disc %",
        "avg_rating":     "Avg Rating",
        "sentiment_score":"Sentiment /100",
        "total_products": "Products",
        "total_reviews":  "Reviews",
        "positioning":    "Positioning",
    }
    snap = summary[[c for c in display_cols if c in summary.columns]].copy()
    snap = snap.rename(columns=display_cols)

    st.dataframe(
        snap.style
        .format({
            "Avg Price (₹)":    "₹{:,.0f}",
            "Avg Disc %":       "{:.1f}%",
            "Avg Rating":       "{:.2f} ★",
            "Sentiment /100":   "{:.0f}",
        })
        .background_gradient(subset=["Sentiment /100"], cmap="RdYlGn")
        .background_gradient(subset=["Avg Disc %"], cmap="RdYlGn_r"),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row 1 ──────────────────────────────────────────────────────────
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(bar_avg_price(summary), use_container_width=True)
    with col_r:
        st.plotly_chart(bar_sentiment(summary), use_container_width=True)

    # ── Price vs Sentiment positioning map ────────────────────────────────────
    st.markdown("### Positioning map — Price vs Sentiment")
    st.caption("Bubble size = total review volume. Top-right = premium + high sentiment (ideal). Bottom-right = expensive but poorly rated.")
    st.plotly_chart(scatter_price_vs_sentiment(summary), use_container_width=True)

    # ── Charts row 2 ──────────────────────────────────────────────────────────
    col_l2, col_r2 = st.columns(2)
    with col_l2:
        st.markdown("### Sentiment breakdown")
        st.plotly_chart(stacked_sentiment(summary), use_container_width=True)
    with col_r2:
        st.markdown("### Value-for-money ranking")
        st.caption("Sentiment score ÷ avg price × 1000 — who gives you the most for your rupee")
        st.plotly_chart(bar_value_for_money(summary), use_container_width=True)

    # ── Positioning legend ────────────────────────────────────────────────────
    st.markdown("### Market positioning")
    pos_counts = summary["positioning"].value_counts()
    col_a, col_b, col_c = st.columns(3)
    for col, label, color in [
        (col_a, "Premium",     "#4F8EF7"),
        (col_b, "Mid-Market",  "#43D39E"),
        (col_c, "Value",       "#F7B731"),
    ]:
        with col:
            brands_in = summary[summary["positioning"] == label]["brand"].tolist()
            st.markdown(
                f"""<div style="background:#0F172A;border:1px solid {color};border-radius:10px;
                                padding:14px;text-align:center;">
                  <div style="color:{color};font-weight:600;font-size:14px;">{label}</div>
                  <div style="color:#CBD5E1;font-size:13px;margin-top:6px;">
                    {', '.join(brands_in) if brands_in else '—'}
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )
