"""
view_comparison.py  —  Dashboard Tab 2: Brand Comparison
"""
from __future__ import annotations

import json

import streamlit as st
import pandas as pd

from dashboard.data_loader import get_brand_summary, load_themes
from dashboard.charts import (
    bar_avg_discount, scatter_discount_vs_sentiment,
    radar_aspect_scores, heatmap_aspects, price_box,
    bar_avg_price, bar_rating, BRAND_COLORS,
)
from dashboard.data_loader import load_products


def _score_pill(score: float | None) -> str:
    if score is None:
        return "<span style='color:#475569'>–</span>"
    color = "#43D39E" if score >= 0.7 else ("#F7B731" if score >= 0.5 else "#F76C6C")
    label = "Good" if score >= 0.7 else ("Ok" if score >= 0.5 else "Poor")
    return (
        f"<span style='background:{color}22;color:{color};border:1px solid {color};"
        f"border-radius:20px;padding:2px 9px;font-size:11px;font-weight:600'>"
        f"{score:.2f} {label}</span>"
    )


def _theme_chips(themes: list, color: str) -> str:
    chips = "".join(
        f"<span style='background:{color}15;color:{color};border:1px solid {color}44;"
        f"border-radius:12px;padding:3px 10px;font-size:11px;margin:2px;display:inline-block'>"
        f"{t}</span>"
        for t in (themes or [])[:4]
    )
    return chips or "<span style='color:#475569'>—</span>"


def render_comparison(selected_brands: list[str]):
    st.markdown("## 🔍 Brand Comparison")
    st.caption("Side-by-side benchmarking of selected brands across all key dimensions.")

    summary  = get_brand_summary()
    themes   = load_themes()
    products = load_products()

    if summary.empty:
        st.info("No data available. Generate sample data from the sidebar.")
        return

    summary = summary[summary["brand"].isin(selected_brands)].copy()

    # ── Metric comparison table ───────────────────────────────────────────────
    st.markdown("### Key metrics — side by side")

    num_brands = len(selected_brands)
    cols = st.columns(num_brands)

    for col, brand in zip(cols, selected_brands):
        row   = summary[summary["brand"] == brand]
        if row.empty:
            continue
        row   = row.iloc[0]
        bcolor = BRAND_COLORS.get(brand, "#94A3B8")
        t      = themes.get(brand, {})
        pos    = t.get("positive_themes", [])
        neg    = t.get("negative_themes", [])
        asp    = t.get("aspect_scores", {})

        with col:
            st.markdown(
                f"""<div style="background:#0F172A;border:1px solid {bcolor};
                                border-radius:12px;padding:18px 14px;">
                  <div style="color:{bcolor};font-size:16px;font-weight:700;
                              margin-bottom:12px;text-align:center">{brand}</div>

                  <div style="display:flex;justify-content:space-between;
                              padding:6px 0;border-bottom:1px solid #1E293B">
                    <span style="color:#94A3B8;font-size:12px">Avg Price</span>
                    <span style="color:#F8FAFC;font-weight:600">₹{row['avg_price']:,.0f}</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;
                              padding:6px 0;border-bottom:1px solid #1E293B">
                    <span style="color:#94A3B8;font-size:12px">Avg Discount</span>
                    <span style="color:#F7B731;font-weight:600">{row['avg_discount']:.1f}%</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;
                              padding:6px 0;border-bottom:1px solid #1E293B">
                    <span style="color:#94A3B8;font-size:12px">Avg Rating</span>
                    <span style="color:#F8FAFC;font-weight:600">★ {row['avg_rating']:.2f}</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;
                              padding:6px 0;border-bottom:1px solid #1E293B">
                    <span style="color:#94A3B8;font-size:12px">Sentiment</span>
                    <span style="color:#43D39E;font-weight:600">{row['sentiment_score']:.0f}/100</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;
                              padding:6px 0;border-bottom:1px solid #1E293B">
                    <span style="color:#94A3B8;font-size:12px">+ve Reviews</span>
                    <span style="color:#43D39E;font-weight:600">{row['positive_pct']:.0f}%</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;
                              padding:6px 0;border-bottom:1px solid #1E293B">
                    <span style="color:#94A3B8;font-size:12px">−ve Reviews</span>
                    <span style="color:#F76C6C;font-weight:600">{row['negative_pct']:.0f}%</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;
                              padding:6px 0;border-bottom:1px solid #1E293B">
                    <span style="color:#94A3B8;font-size:12px">Products</span>
                    <span style="color:#F8FAFC;font-weight:600">{int(row['total_products'])}</span>
                  </div>
                  <div style="display:flex;justify-content:space-between;padding:6px 0">
                    <span style="color:#94A3B8;font-size:12px">Positioning</span>
                    <span style="color:#A78BFA;font-weight:600">{row['positioning']}</span>
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

            # Pros
            st.markdown(
                f"""<div style="margin-top:10px">
                  <div style="color:#43D39E;font-size:11px;font-weight:600;
                              margin-bottom:4px">✅ STRENGTHS</div>
                  {_theme_chips(pos, '#43D39E')}
                </div>""",
                unsafe_allow_html=True,
            )
            # Cons
            st.markdown(
                f"""<div style="margin-top:8px;margin-bottom:16px">
                  <div style="color:#F76C6C;font-size:11px;font-weight:600;
                              margin-bottom:4px">⚠️ WEAKNESSES</div>
                  {_theme_chips(neg, '#F76C6C')}
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row 1 ──────────────────────────────────────────────────────────
    cl, cr = st.columns(2)
    with cl:
        st.plotly_chart(bar_avg_discount(summary), use_container_width=True)
    with cr:
        st.plotly_chart(scatter_discount_vs_sentiment(summary), use_container_width=True)

    # ── Radar chart ───────────────────────────────────────────────────────────
    st.markdown("### Aspect-level comparison")
    st.caption("Compares wheel quality, handle, zipper, material, durability, size, and weight across brands.")
    st.plotly_chart(radar_aspect_scores(themes, selected_brands), use_container_width=True)

    # ── Heatmap ───────────────────────────────────────────────────────────────
    st.markdown("### Aspect score heatmap")
    st.plotly_chart(heatmap_aspects(themes, selected_brands), use_container_width=True)

    # ── Price box ─────────────────────────────────────────────────────────────
    st.markdown("### Price spread by brand")
    st.caption("Box plot shows min, Q1, median, Q3, and max prices for each brand.")
    if not products.empty:
        st.plotly_chart(price_box(products, selected_brands), use_container_width=True)

    # ── Sortable comparison table ─────────────────────────────────────────────
    st.markdown("### Sortable comparison table")

    cols_map = {
        "brand":          "Brand",
        "avg_price":      "Avg Price (₹)",
        "avg_discount":   "Disc %",
        "avg_rating":     "Rating ★",
        "sentiment_score":"Sentiment",
        "positive_pct":   "+ve %",
        "negative_pct":   "−ve %",
        "value_score":    "VFM Score",
        "total_products": "Products",
        "total_reviews":  "Reviews",
        "positioning":    "Tier",
    }
    tbl = summary[[c for c in cols_map if c in summary.columns]].rename(columns=cols_map)
    sort_col = st.selectbox("Sort by", list(tbl.columns)[1:], index=3)
    asc       = st.checkbox("Ascending", value=False)
    tbl = tbl.sort_values(sort_col, ascending=asc)

    st.dataframe(
        tbl.style
        .format({
            "Avg Price (₹)": "₹{:,.0f}",
            "Disc %":        "{:.1f}%",
            "Rating ★":      "{:.2f}",
            "Sentiment":     "{:.0f}",
            "+ve %":         "{:.0f}%",
            "−ve %":         "{:.0f}%",
            "VFM Score":     "{:.3f}",
        })
        .background_gradient(subset=["Sentiment"], cmap="RdYlGn")
        .background_gradient(subset=["Disc %"],    cmap="RdYlGn_r"),
        use_container_width=True,
        hide_index=True,
    )
