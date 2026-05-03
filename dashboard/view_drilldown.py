"""
view_drilldown.py  —  Dashboard Tab 3: Product Drilldown
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from dashboard.data_loader import load_products, load_reviews, load_themes
from dashboard.charts import scatter_products, BRAND_COLORS


def _star_html(rating: float) -> str:
    full  = int(rating)
    half  = 1 if (rating - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + ("½" if half else "") + "☆" * empty


def _review_card(rev: pd.Series, color: str):
    label_color = {
        "positive": "#43D39E",
        "negative": "#F76C6C",
        "neutral":  "#94A3B8",
    }.get(str(rev.get("sentiment_label", "neutral")).lower(), "#94A3B8")

    st.markdown(
        f"""<div style="background:#0F172A;border-left:3px solid {label_color};
                        border-radius:0 8px 8px 0;padding:12px 14px;margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;align-items:center;
                      margin-bottom:6px;">
            <span style="color:#F8FAFC;font-size:13px;font-weight:500">
              {_star_html(float(rev.get('rating', 0)))} {rev.get('title', '')[:60]}
            </span>
            <span style="color:{label_color};font-size:11px;font-weight:600;
                         background:{label_color}20;border-radius:10px;padding:2px 8px">
              {str(rev.get('sentiment_label', '')).upper()}
            </span>
          </div>
          <div style="color:#CBD5E1;font-size:12px;line-height:1.6">
            {str(rev.get('body', ''))[:350]}{"..." if len(str(rev.get('body', ''))) > 350 else ""}
          </div>
          <div style="color:#475569;font-size:11px;margin-top:6px">
            {"✅ Verified" if rev.get('verified') else ""}  {rev.get('date', '')}
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_drilldown(selected_brands: list[str]):
    st.markdown("## 🧳 Product Drilldown")
    st.caption("Explore individual products, prices, discounts, and customer reviews.")

    products_df = load_products()
    reviews_df  = load_reviews()
    themes      = load_themes()

    if products_df.empty:
        st.info("No product data found. Generate sample data from the sidebar.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.container():
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
        with fc1:
            brand_sel = st.selectbox(
                "Select Brand",
                [b for b in selected_brands if b in products_df["brand"].unique()],
            )
        with fc2:
            size_opts = ["All"] + sorted(products_df["size_category"].dropna().unique().tolist())
            size_sel  = st.selectbox("Size Category", size_opts)
        with fc3:
            price_min = int(products_df["price"].min())
            price_max = int(products_df["price"].max())
            price_range = st.slider(
                "Price Range (₹)", price_min, price_max, (price_min, price_max), step=100
            )
        with fc4:
            min_rating = st.slider("Min Rating ★", 1.0, 5.0, 1.0, step=0.5)

    # Apply filters
    filtered = products_df[products_df["brand"] == brand_sel].copy()
    if size_sel != "All":
        filtered = filtered[filtered["size_category"] == size_sel]
    filtered = filtered[
        (filtered["price"] >= price_range[0]) &
        (filtered["price"] <= price_range[1]) &
        (filtered["rating"] >= min_rating)
    ]

    st.markdown(f"**{len(filtered)} products** matching filters for **{brand_sel}**")

    # ── Product scatter ───────────────────────────────────────────────────────
    st.plotly_chart(scatter_products(products_df, brand_sel), use_container_width=True)

    if filtered.empty:
        st.warning("No products match your filters.")
        return

    # ── Product cards ─────────────────────────────────────────────────────────
    st.markdown("### Products")
    bcolor = BRAND_COLORS.get(brand_sel, "#94A3B8")

    sort_by  = st.selectbox("Sort products by", ["price", "rating", "discount_pct", "review_count"], index=0)
    sort_asc = st.checkbox("Ascending order", value=True)
    filtered = filtered.sort_values(sort_by, ascending=sort_asc).reset_index(drop=True)

    for idx, row in filtered.iterrows():
        saving = row["mrp"] - row["price"]

        with st.expander(
            f"🧳 {row['title'][:65]}... — ₹{row['price']:,.0f}  |  ★ {row['rating']:.1f}",
            expanded=False,
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Selling Price", f"₹{row['price']:,.0f}")
            c2.metric("List Price (MRP)", f"₹{row['mrp']:,.0f}", delta=f"-₹{saving:,.0f}", delta_color="normal")
            c3.metric("Discount", f"{row['discount_pct']:.1f}%")
            c4.metric("Rating", f"★ {row['rating']:.1f}", help=f"{int(row['review_count']):,} reviews")

            st.markdown(f"**Size category:** {row.get('size_category', '—')}")
            if row.get("url"):
                st.markdown(f"[View on Amazon ↗]({row['url']})")

            # Brand-level themes as a proxy for product themes
            brand_themes = themes.get(brand_sel, {})
            tc_l, tc_r = st.columns(2)
            with tc_l:
                st.markdown("**✅ Common Praise (brand-level)**")
                for t in brand_themes.get("positive_themes", [])[:3]:
                    st.markdown(f"- {t}")
            with tc_r:
                st.markdown("**⚠️ Common Complaints (brand-level)**")
                for t in brand_themes.get("negative_themes", [])[:3]:
                    st.markdown(f"- {t}")

            # Review samples for this product ASIN
            if not reviews_df.empty and "asin" in reviews_df.columns:
                prod_reviews = reviews_df[reviews_df["asin"] == row["asin"]]
            else:
                prod_reviews = reviews_df[reviews_df["brand"] == brand_sel] if not reviews_df.empty else pd.DataFrame()

            if not prod_reviews.empty:
                st.markdown("---")
                st.markdown("**Customer Reviews**")
                sent_filter = st.radio(
                    "Filter reviews",
                    ["All", "Positive", "Negative", "Neutral"],
                    horizontal=True,
                    key=f"rf_{row['asin']}",
                )
                if sent_filter != "All" and "sentiment_label" in prod_reviews.columns:
                    prod_reviews = prod_reviews[
                        prod_reviews["sentiment_label"].str.lower() == sent_filter.lower()
                    ]

                for _, rev in prod_reviews.head(5).iterrows():
                    _review_card(rev, bcolor)

    # ── Aspect drilldown for selected brand ───────────────────────────────────
    st.markdown("---")
    st.markdown(f"### {brand_sel} — Aspect scores")
    aspects = load_themes().get(brand_sel, {}).get("aspect_scores", {})
    mentions = load_themes().get(brand_sel, {}).get("aspect_mentions", {})

    if aspects:
        aspect_df = pd.DataFrame([
            {"Aspect": a.capitalize(), "Score": v, "Mentions": mentions.get(a, "–")}
            for a, v in aspects.items() if v is not None
        ]).sort_values("Score", ascending=False)

        st.dataframe(
            aspect_df.style
            .format({"Score": "{:.2f}"})
            .background_gradient(subset=["Score"], cmap="RdYlGn"),
            use_container_width=True,
            hide_index=True,
        )

        verdict = load_themes().get(brand_sel, {}).get("one_line_verdict", "")
        if verdict:
            st.info(f"**AI Verdict:** {verdict}")
