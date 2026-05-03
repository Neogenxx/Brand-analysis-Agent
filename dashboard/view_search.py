"""
view_search.py  —  Dashboard Tab 5: Semantic Review Search
"""
from __future__ import annotations

import streamlit as st

from dashboard.data_loader import load_reviews, get_available_brands
from dashboard.charts import BRAND_COLORS


def render_search(selected_brands: list[str]):
    st.markdown("## 🔎 Semantic Review Search")
    st.markdown(
        "<p style='color:#94A3B8'>Search across all customer reviews using natural language. "
        "Powered by sentence-transformer embeddings + ChromaDB vector search.</p>",
        unsafe_allow_html=True,
    )

    # ── Search form ───────────────────────────────────────────────────────────
    sc1, sc2, sc3, sc4 = st.columns([4, 2, 2, 1])
    with sc1:
        query = st.text_input(
            "Search query",
            placeholder='e.g. "wheels broke after one trip" or "good for cabin size"',
            label_visibility="collapsed",
        )
    with sc2:
        brand_opts = ["All brands"] + selected_brands
        brand_f    = st.selectbox("Brand", brand_opts, label_visibility="collapsed")
    with sc3:
        sent_opts = ["All sentiments", "positive", "negative", "neutral"]
        sent_f    = st.selectbox("Sentiment", sent_opts, label_visibility="collapsed")
    with sc4:
        n_results = st.number_input("Results", 1, 30, 10, label_visibility="collapsed")

    if not query:
        st.info("Enter a search query above to find semantically similar reviews.")
        _show_keyword_fallback(selected_brands)
        return

    # ── Vector search ─────────────────────────────────────────────────────────
    brand_arg = None if brand_f == "All brands" else brand_f
    sent_arg  = None if sent_f  == "All sentiments" else sent_f

    try:
        from vector_db.chroma_store import query_reviews, get_collection_stats
        stats = get_collection_stats()

        if stats["total_documents"] == 0:
            st.warning("ChromaDB index is empty. Using keyword fallback search.")
            _keyword_search(query, brand_arg, sent_arg, int(n_results), selected_brands)
            return

        with st.spinner(f"Searching {stats['total_documents']:,} indexed reviews..."):
            results = query_reviews(
                query,
                brand=brand_arg,
                n_results=int(n_results),
                sentiment=sent_arg,
            )

        if not results:
            st.warning("No results found. Try a different query or remove filters.")
            return

        st.success(f"Found **{len(results)}** semantically relevant reviews")
        _render_results(results)

    except Exception as e:
        st.warning(f"Vector search unavailable ({e}). Using keyword fallback.")
        _keyword_search(query, brand_arg, sent_arg, int(n_results), selected_brands)


def _render_results(results: list[dict]):
    for i, res in enumerate(results):
        brand     = res.get("brand", "Unknown")
        bcolor    = BRAND_COLORS.get(brand, "#94A3B8")
        label     = res.get("label", "neutral")
        label_color = {
            "positive": "#43D39E",
            "negative": "#F76C6C",
            "neutral":  "#94A3B8",
        }.get(label, "#94A3B8")

        similarity = round((1 - res.get("distance", 0.5)) * 100, 1)

        st.markdown(
            f"""
            <div style="background:#0F172A;border:1px solid #1E293B;
                        border-left:3px solid {bcolor};border-radius:0 10px 10px 0;
                        padding:14px 16px;margin-bottom:12px">
              <div style="display:flex;justify-content:space-between;
                          align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:6px">
                <span style="color:{bcolor};font-weight:600;font-size:13px">
                  {brand}
                </span>
                <div style="display:flex;gap:8px;align-items:center">
                  <span style="color:{label_color};background:{label_color}20;
                               border:1px solid {label_color}44;border-radius:10px;
                               padding:2px 8px;font-size:11px">
                    {label.upper()}
                  </span>
                  <span style="color:#94A3B8;font-size:11px">
                    {"★" * int(res.get("rating", 0))} {res.get("rating", 0):.0f}★
                  </span>
                  <span style="color:#475569;font-size:11px">
                    {similarity:.0f}% match
                  </span>
                </div>
              </div>
              <div style="color:#CBD5E1;font-size:13px;line-height:1.6">
                {res.get("body", "")[:400]}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _keyword_search(
    query: str,
    brand: str | None,
    sentiment: str | None,
    n: int,
    selected_brands: list[str],
):
    """Simple keyword fallback when ChromaDB is unavailable."""
    reviews_df = load_reviews()
    if reviews_df.empty:
        st.warning("No review data available.")
        return

    df = reviews_df[reviews_df["brand"].isin(selected_brands)].copy()
    if brand:
        df = df[df["brand"] == brand]
    if sentiment and "sentiment_label" in df.columns:
        df = df[df["sentiment_label"].str.lower() == sentiment]

    mask = df["body"].str.lower().str.contains(
        "|".join(query.lower().split()), na=False
    )
    results_df = df[mask].head(n)

    if results_df.empty:
        st.warning("No keyword matches found.")
        return

    st.info(f"Keyword fallback: found {len(results_df)} matches")
    for _, row in results_df.iterrows():
        _render_results([{
            "brand":    row.get("brand", ""),
            "body":     row.get("body", ""),
            "rating":   row.get("rating", 0),
            "label":    row.get("sentiment_label", "neutral"),
            "distance": 0.2,
        }])


def _show_keyword_fallback(selected_brands: list[str]):
    """Show popular search suggestions."""
    st.markdown("### 💡 Suggested searches")
    suggestions = [
        "wheels broke after one trip",
        "zipper quality poor",
        "good value for money",
        "lightweight and spacious",
        "durable hard shell",
        "handle gets stuck",
        "excellent for cabin travel",
        "not worth the price",
    ]

    cols = st.columns(2)
    for i, sug in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(f"🔍 {sug}", key=f"sug_{i}", use_container_width=True):
                st.session_state["search_query"] = sug
                st.rerun()
