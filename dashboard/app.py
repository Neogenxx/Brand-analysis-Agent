"""
app.py  —  Brand Analysis Agent | Main Streamlit Dashboard
===========================================================
Run: streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path regardless of where streamlit is invoked
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from dashboard.data_loader import (
    data_is_ready, get_available_brands, clear_all_cache,
    load_products, load_reviews, load_sentiment, load_insights,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Brand Analysis Agent",
    page_icon="🧳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global dark-mode CSS ──────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Base */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background-color: #020817; }
    section[data-testid="stSidebar"] { background-color: #0A0F1E; border-right: 1px solid #1E293B; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #0F172A; border: 1px solid #1E293B;
        border-radius: 12px; padding: 16px;
    }
    [data-testid="metric-container"] label { color: #94A3B8 !important; font-size: 12px !important; }
    [data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #F8FAFC !important; font-size: 24px !important; font-weight: 700 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { background: #0F172A; border-radius: 10px; padding: 4px; gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px; padding: 8px 18px; color: #64748B;
        font-weight: 500; border: none;
    }
    .stTabs [aria-selected="true"] {
        background: #1E293B; color: #F8FAFC !important; font-weight: 600;
    }

    /* Expanders */
    .streamlit-expanderHeader { background: #0F172A; border-radius: 8px; color: #CBD5E1 !important; }

    /* Buttons */
    .stButton > button {
        background: #1E293B; color: #CBD5E1; border: 1px solid #334155;
        border-radius: 8px; font-weight: 500;
        transition: all .2s ease;
    }
    .stButton > button:hover { background: #334155; color: #F8FAFC; border-color: #4F8EF7; }

    /* Selectbox / slider */
    .stSelectbox > div, .stSlider > div { color: #CBD5E1; }

    /* Dataframe */
    .stDataFrame { border-radius: 10px; overflow: hidden; }

    /* Input */
    .stTextInput > div > div { background: #0F172A; border: 1px solid #1E293B; border-radius: 8px; }
    .stTextInput input { color: #F8FAFC; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0A0F1E; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }

    /* Remove default padding */
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:8px">
      <span style="font-size:38px">🧳</span>
      <div>
        <h1 style="margin:0;color:#F8FAFC;font-size:28px;font-weight:800;
                   letter-spacing:-0.5px">Brand Analysis Agent</h1>
        <p style="margin:0;color:#64748B;font-size:13px">
          Competitive intelligence dashboard — Luggage brands on Amazon India
        </p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<h2 style='color:#F8FAFC;font-size:18px;font-weight:700;margin-bottom:4px'>"
        "⚙️ Controls</h2>",
        unsafe_allow_html=True,
    )

    # ── Data status ───────────────────────────────────────────────────────────
    ready = data_is_ready()
    if ready:
        products_df = load_products()
        reviews_df  = load_reviews()
        st.success(
            f"✅ Data ready\n\n"
            f"**{len(products_df):,}** products | **{len(reviews_df):,}** reviews"
        )
    else:
        st.warning("⚠️ No data found. Generate sample data below.")

    st.markdown("---")

    # ── Pipeline controls ─────────────────────────────────────────────────────
    st.markdown("**🔧 Data pipeline**")

    if st.button("📦 Generate Sample Data", use_container_width=True, help="Generates realistic mock data. No scraping or API key required."):
        with st.spinner("Generating sample data..."):
            try:
                from utils.sample_data import save_sample_data
                from agents.langgraph_pipeline import run_pipeline
                clear_all_cache()
                save_sample_data()
                run_pipeline()
                st.success("Sample data + insights generated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("🕷️ Run Scraper", use_container_width=True, help="Scrapes Amazon India. Requires Playwright installed."):
        with st.spinner("Scraping Amazon India... (may take 5–15 min)"):
            try:
                import asyncio
                from scraper.scraper       import run_scraper
                from processing.cleaning   import run_cleaning
                from processing.sentiment  import run_sentiment
                from processing.themes     import run_themes
                from agents.langgraph_pipeline import run_pipeline
                clear_all_cache()
                asyncio.run(run_scraper())
                run_cleaning()
                run_sentiment(use_llm=True)
                run_themes(use_llm=True)
                run_pipeline()
                st.success("Scraping + pipeline complete!")
                st.rerun()
            except Exception as e:
                st.error(f"Scraper error: {e}")

    if st.button("🔄 Refresh Insights Only", use_container_width=True):
        with st.spinner("Running LangGraph pipeline..."):
            try:
                from agents.langgraph_pipeline import run_pipeline
                clear_all_cache()
                run_pipeline()
                st.success("Insights refreshed!")
                st.rerun()
            except Exception as e:
                st.error(f"Pipeline error: {e}")

    if st.button("🗑️ Clear Cache", use_container_width=True):
        clear_all_cache()
        st.success("Cache cleared")
        st.rerun()

    st.markdown("---")

    # ── Brand filter ──────────────────────────────────────────────────────────
    available_brands = get_available_brands()
    st.markdown("**🏷️ Brand filter**")
    selected_brands = st.multiselect(
        "Select brands to display",
        options=available_brands,
        default=available_brands,
        label_visibility="collapsed",
    )
    if not selected_brands:
        selected_brands = available_brands

    # ── Insights count ────────────────────────────────────────────────────────
    insights = load_insights()
    if insights:
        st.markdown("---")
        st.markdown(f"**🤖 {len(insights)} agent insights** ready")

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        "<div style='color:#334155;font-size:11px;text-align:center'>"
        "Brand Analysis Agent v1.0<br>"
        "Moonshot AI Internship Assignment"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Guard: no data ────────────────────────────────────────────────────────────
if not ready:
    st.markdown(
        """
        <div style="background:#0F172A;border:1px solid #1E293B;border-radius:16px;
                    padding:40px;text-align:center;margin-top:40px">
          <div style="font-size:54px;margin-bottom:16px">📭</div>
          <h2 style="color:#F8FAFC;margin-bottom:8px">No data yet</h2>
          <p style="color:#64748B;font-size:14px">
            Click <strong style="color:#4F8EF7">Generate Sample Data</strong> in the sidebar
            to instantly populate the dashboard with realistic mock data for 6 luggage brands.
            <br><br>
            Or click <strong style="color:#4F8EF7">Run Scraper</strong> to pull live data from Amazon India
            (requires Playwright and more time).
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Overview",
    "🔍 Brand Comparison",
    "🧳 Product Drilldown",
    "🤖 Agent Insights",
    "🔎 Review Search",
])

with tab1:
    from dashboard.view_overview    import render_overview
    render_overview(selected_brands)

with tab2:
    from dashboard.view_comparison  import render_comparison
    render_comparison(selected_brands)

with tab3:
    from dashboard.view_drilldown   import render_drilldown
    render_drilldown(selected_brands)

with tab4:
    from dashboard.view_insights    import render_insights
    render_insights(selected_brands)

with tab5:
    from dashboard.view_search      import render_search
    render_search(selected_brands)
