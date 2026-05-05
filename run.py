"""
Usage:
  python run.py                  → generate sample data + launch dashboard
  python run.py --scrape         → run live scraper + full pipeline + launch dashboard
  python run.py --api            → launch FastAPI backend only
  python run.py --pipeline-only  → run full pipeline without launching UI
"""
from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _banner():
    print("""
              Brand Analysis Agent 
""")


def step(msg: str):
    print(f"\n{'─'*50}")
    print(f"  ▶  {msg}")
    print(f"{'─'*50}")


def generate_sample():
    step("Generating sample data (no scraping needed)")
    from utils.sample_data import save_sample_data
    save_sample_data()


def run_scraper():
    step("Running Playwright scraper on Amazon India")
    from scraper.scraper import run_scraper as _scrape
    asyncio.run(_scrape())


def run_cleaning():
    step("Cleaning and normalising raw data")
    from processing.cleaning import run_cleaning as _clean
    _clean()


def run_sentiment():
    step("Running sentiment analysis (VADER + optional LLM)")
    from processing.sentiment import run_sentiment as _sent
    _sent(use_llm=True)


def run_themes():
    step("Extracting themes and aspect scores")
    from processing.themes import run_themes as _themes
    _themes(use_llm=True)


def run_pipeline():
    step("Running LangGraph Agent Insights pipeline")
    from agents.langgraph_pipeline import run_pipeline as _pipeline
    insights = _pipeline()
    print(f"\n  ✓  Generated {len(insights)} agent insights")
    for ins in insights:
        print(f"     [{ins.get('rank','?')}] {ins.get('title','')}")


def launch_dashboard():
    step("Launching Streamlit dashboard")
    print("  Dashboard → http://localhost:8501")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(ROOT / "dashboard" / "app.py"),
        "--server.port", "8501",
        "--server.headless", "false",
        "--theme.base", "dark",
        "--theme.backgroundColor", "#020817",
        "--theme.secondaryBackgroundColor", "#0F172A",
        "--theme.textColor", "#F8FAFC",
        "--theme.primaryColor", "#4F8EF7",
    ], check=True)


def launch_api():
    step("Launching FastAPI backend")
    print("  API docs → http://localhost:8000/docs")
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "api.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
    ], check=True)


def main():
    _banner()
    parser = argparse.ArgumentParser(description="Brand Analysis Agent")
    parser.add_argument("--scrape",         action="store_true", help="Run live scraper instead of sample data")
    parser.add_argument("--api",            action="store_true", help="Launch FastAPI backend only")
    parser.add_argument("--pipeline-only",  action="store_true", help="Run pipeline without launching UI")
    parser.add_argument("--no-ui",          action="store_true", help="Skip launching the dashboard")
    args = parser.parse_args()

    if args.api:
        launch_api()
        return

    # Data step
    if args.scrape:
        run_scraper()
        run_cleaning()
    else:
        generate_sample()

    # Analysis pipeline
    run_sentiment()
    run_themes()
    run_pipeline()

    if args.pipeline_only or args.no_ui:
        print("\n  Pipeline complete. Data saved to data/processed/")
        return

    # Launch dashboard
    launch_dashboard()


if __name__ == "__main__":
    main()
