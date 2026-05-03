"""
charts.py
---------
Reusable Plotly chart factory functions for the Brand Analysis Agent dashboard.
All functions return a go.Figure ready for st.plotly_chart().
"""
from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ── Colour palette ────────────────────────────────────────────────────────────
BRAND_COLORS = {
    "Safari":             "#4F8EF7",
    "Skybags":            "#F76C6C",
    "American Tourister": "#43D39E",
    "VIP":                "#F7B731",
    "Aristocrat":         "#A78BFA",
    "Nasher Miles":       "#FB923C",
}
DEFAULT_COLOR = "#94A3B8"

CATEGORY_COLORS = {
    "Premium":     "#4F8EF7",
    "Mid-Market":  "#43D39E",
    "Value":       "#F7B731",
}

CONFIDENCE_COLORS = {
    "High":   "#43D39E",
    "Medium": "#F7B731",
    "Low":    "#F76C6C",
}

CHART_FONT = dict(family="Inter, sans-serif", size=12, color="#CBD5E1")
LAYOUT_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font         =CHART_FONT,
    legend       =dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#CBD5E1")),
    margin       =dict(l=20, r=20, t=40, b=20),
)

def _brand_color(brand: str) -> str:
    return BRAND_COLORS.get(brand, DEFAULT_COLOR)

def _color_list(brands: list[str]) -> list[str]:
    return [_brand_color(b) for b in brands]


# ── Bar charts ────────────────────────────────────────────────────────────────

def bar_avg_price(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("avg_price", ascending=False)
    fig = go.Figure(go.Bar(
        x=df["brand"], y=df["avg_price"],
        marker_color=_color_list(df["brand"].tolist()),
        text=df["avg_price"].apply(lambda p: f"₹{p:,.0f}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Avg Price: ₹%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title="Average Selling Price by Brand",
        yaxis_title="Price (₹)", xaxis_title="",
        yaxis=dict(gridcolor="#1E293B"),
    )
    return fig


def bar_avg_discount(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("avg_discount", ascending=False)
    fig = go.Figure(go.Bar(
        x=df["brand"], y=df["avg_discount"],
        marker_color=_color_list(df["brand"].tolist()),
        text=df["avg_discount"].apply(lambda d: f"{d:.1f}%"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Avg Discount: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title="Average Discount % by Brand (higher = more discount-dependent)",
        yaxis_title="Discount %", xaxis_title="",
        yaxis=dict(gridcolor="#1E293B"),
    )
    return fig


def bar_sentiment(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("sentiment_score", ascending=False)
    fig = go.Figure(go.Bar(
        x=df["brand"], y=df["sentiment_score"],
        marker_color=_color_list(df["brand"].tolist()),
        text=df["sentiment_score"].apply(lambda s: f"{s:.0f}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Sentiment: %{y:.1f}/100<extra></extra>",
    ))
    fig.add_hline(y=50, line_dash="dot", line_color="#475569",
                  annotation_text="Neutral (50)", annotation_position="right")
    fig.update_layout(
        **LAYOUT_BASE,
        title="Brand Sentiment Score (0–100)",
        yaxis_title="Sentiment Score", xaxis_title="",
        yaxis=dict(gridcolor="#1E293B", range=[0, 105]),
    )
    return fig


def bar_rating(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("avg_rating", ascending=False)
    fig = go.Figure(go.Bar(
        x=df["brand"], y=df["avg_rating"],
        marker_color=_color_list(df["brand"].tolist()),
        text=df["avg_rating"].apply(lambda r: f"★ {r:.2f}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Avg Rating: %{y:.2f}★<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title="Average Star Rating by Brand",
        yaxis_title="Rating (out of 5)", xaxis_title="",
        yaxis=dict(gridcolor="#1E293B", range=[0, 5.5]),
    )
    return fig


# ── Scatter ───────────────────────────────────────────────────────────────────

def scatter_price_vs_sentiment(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for _, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["avg_price"]],
            y=[row["sentiment_score"]],
            mode="markers+text",
            marker=dict(
                size=max(12, min(40, row["total_reviews"] / 500 + 16)),
                color=_brand_color(row["brand"]),
                opacity=0.85,
                line=dict(color="white", width=1.5),
            ),
            text=[row["brand"]],
            textposition="top center",
            name=row["brand"],
            hovertemplate=(
                f"<b>{row['brand']}</b><br>"
                f"Avg Price: ₹{row['avg_price']:,.0f}<br>"
                f"Sentiment: {row['sentiment_score']:.1f}/100<br>"
                f"Avg Discount: {row['avg_discount']:.1f}%<br>"
                f"Reviews: {int(row['total_reviews']):,}<extra></extra>"
            ),
        ))

    price_mid = df["avg_price"].median()
    sent_mid  = df["sentiment_score"].median()

    fig.add_hline(y=sent_mid,  line_dash="dot", line_color="#334155",
                  annotation_text="Avg Sentiment", annotation_position="right")
    fig.add_vline(x=price_mid, line_dash="dot", line_color="#334155",
                  annotation_text="Avg Price", annotation_position="top")

    fig.update_layout(
        **LAYOUT_BASE,
        title="Price vs Sentiment — Bubble size = review volume",
        xaxis_title="Average Price (₹)",
        yaxis_title="Sentiment Score (0–100)",
        showlegend=False,
        xaxis=dict(gridcolor="#1E293B"),
        yaxis=dict(gridcolor="#1E293B"),
    )
    return fig


def scatter_discount_vs_sentiment(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for _, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["avg_discount"]],
            y=[row["sentiment_score"]],
            mode="markers+text",
            marker=dict(
                size=18,
                color=_brand_color(row["brand"]),
                opacity=0.85,
                line=dict(color="white", width=1.5),
            ),
            text=[row["brand"]],
            textposition="top center",
            name=row["brand"],
            hovertemplate=(
                f"<b>{row['brand']}</b><br>"
                f"Avg Discount: {row['avg_discount']:.1f}%<br>"
                f"Sentiment: {row['sentiment_score']:.1f}/100<extra></extra>"
            ),
        ))

    fig.update_layout(
        **LAYOUT_BASE,
        title="Discount Dependency vs Sentiment (top-left = discount-reliant and poor quality)",
        xaxis_title="Average Discount %",
        yaxis_title="Sentiment Score (0–100)",
        showlegend=False,
        xaxis=dict(gridcolor="#1E293B"),
        yaxis=dict(gridcolor="#1E293B"),
    )
    return fig


# ── Radar / Spider ────────────────────────────────────────────────────────────

def radar_aspect_scores(themes: dict, selected_brands: list[str]) -> go.Figure:
    aspects = ["wheels", "handle", "zipper", "material", "durability", "size", "weight"]
    fig = go.Figure()

    for brand in selected_brands:
        brand_themes = themes.get(brand, {})
        scores = brand_themes.get("aspect_scores", {})
        values = [scores.get(a) or 0.5 for a in aspects]
        values_closed = values + [values[0]]
        cats_closed   = aspects + [aspects[0]]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=cats_closed,
            fill="toself",
            fillcolor=_brand_color(brand),
            opacity=0.25,
            line=dict(color=_brand_color(brand), width=2),
            name=brand,
            hovertemplate="%{theta}: %{r:.2f}<extra>" + brand + "</extra>",
        ))

    fig.update_layout(
        **LAYOUT_BASE,
        title="Aspect-Level Sentiment (0 = worst, 1 = best)",
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True, range=[0, 1],
                gridcolor="#334155", tickfont=dict(color="#94A3B8"),
            ),
            angularaxis=dict(gridcolor="#334155", tickfont=dict(color="#CBD5E1")),
        ),
    )
    return fig


# ── Stacked bar: Sentiment breakdown ─────────────────────────────────────────

def stacked_sentiment(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("positive_pct", ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Positive", x=df["brand"], y=df["positive_pct"],
        marker_color="#43D39E",
        hovertemplate="<b>%{x}</b><br>Positive: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Neutral", x=df["brand"],
        y=df.get("neutral_pct", 100 - df["positive_pct"] - df["negative_pct"]).clip(lower=0),
        marker_color="#64748B",
        hovertemplate="<b>%{x}</b><br>Neutral: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Negative", x=df["brand"], y=df["negative_pct"],
        marker_color="#F76C6C",
        hovertemplate="<b>%{x}</b><br>Negative: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        barmode="stack",
        title="Sentiment Breakdown by Brand (%)",
        yaxis_title="% of Reviews", xaxis_title="",
        yaxis=dict(gridcolor="#1E293B"),
    )
    return fig


# ── Price range box / strip ───────────────────────────────────────────────────

def price_box(products_df: pd.DataFrame, selected_brands: list[str]) -> go.Figure:
    df = products_df[products_df["brand"].isin(selected_brands)]
    fig = go.Figure()
    for brand in selected_brands:
        bd = df[df["brand"] == brand]["price"]
        fig.add_trace(go.Box(
            y=bd, name=brand,
            marker_color=_brand_color(brand),
            boxmean=True,
            hovertemplate="<b>" + brand + "</b><br>₹%{y:,.0f}<extra></extra>",
        ))
    fig.update_layout(
        **LAYOUT_BASE,
        title="Price Distribution per Brand",
        yaxis_title="Price (₹)", xaxis_title="",
        yaxis=dict(gridcolor="#1E293B"),
    )
    return fig


# ── Horizontal bar: value-for-money ──────────────────────────────────────────

def bar_value_for_money(df: pd.DataFrame) -> go.Figure:
    df = df.sort_values("value_score", ascending=True)
    fig = go.Figure(go.Bar(
        x=df["value_score"], y=df["brand"],
        orientation="h",
        marker_color=_color_list(df["brand"].tolist()),
        text=df["value_score"].apply(lambda v: f"{v:.2f}"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>VFM Score: %{x:.3f}<extra></extra>",
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title="Value-for-Money Score (Sentiment ÷ Price × 1000)",
        xaxis_title="VFM Score", yaxis_title="",
        xaxis=dict(gridcolor="#1E293B"),
        height=300,
    )
    return fig


# ── Heatmap: aspect scores ────────────────────────────────────────────────────

def heatmap_aspects(themes: dict, brands: list[str]) -> go.Figure:
    aspects = ["wheels", "handle", "zipper", "material", "durability", "size", "weight"]
    z, x, y = [], brands, aspects

    for brand in brands:
        row = []
        asp = themes.get(brand, {}).get("aspect_scores", {})
        for a in aspects:
            row.append(asp.get(a) or 0.5)
        z.append(row)

    fig = go.Figure(go.Heatmap(
        z=z, x=y, y=x,
        colorscale=[[0, "#F76C6C"], [0.5, "#F7B731"], [1, "#43D39E"]],
        zmin=0, zmax=1,
        text=[[f"{v:.2f}" for v in row] for row in z],
        texttemplate="%{text}",
        hovertemplate="<b>%{y}</b> — %{x}: %{z:.2f}<extra></extra>",
        colorbar=dict(
            title="Score",
            tickvals=[0, 0.5, 1],
            ticktext=["Poor", "Average", "Excellent"],
            tickfont=dict(color="#CBD5E1"),
        ),
    ))
    fig.update_layout(
        **LAYOUT_BASE,
        title="Aspect Score Heatmap (0 = worst, 1 = best)",
        height=max(300, len(brands) * 55),
        xaxis=dict(tickfont=dict(color="#CBD5E1")),
        yaxis=dict(tickfont=dict(color="#CBD5E1")),
    )
    return fig


# ── Product-level scatter ─────────────────────────────────────────────────────

def scatter_products(products_df: pd.DataFrame, brand: str) -> go.Figure:
    df = products_df[products_df["brand"] == brand].copy()
    if df.empty:
        return go.Figure()

    fig = px.scatter(
        df, x="price", y="rating",
        size="review_count",
        color="discount_pct",
        color_continuous_scale=["#43D39E", "#F7B731", "#F76C6C"],
        hover_name="title",
        hover_data={"price": ":.0f", "discount_pct": ":.1f", "review_count": True, "rating": True},
        labels={"price": "Price (₹)", "rating": "Rating", "discount_pct": "Discount %"},
        size_max=40,
    )
    fig.update_layout(
        **LAYOUT_BASE,
        title=f"{brand} — Products: Price vs Rating (size = reviews, colour = discount)",
        xaxis=dict(gridcolor="#1E293B"),
        yaxis=dict(gridcolor="#1E293B", range=[0, 5.5]),
        coloraxis_colorbar=dict(tickfont=dict(color="#CBD5E1"), title="Disc %"),
    )
    return fig
