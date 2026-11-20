"""Shared helpers for the Streamlit pages. Reads only committed files (data/snapshot, config,
data/ai_cache, data_quality_report.md): no network and no API key needed."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from fpacopilot import variance as v
from fpacopilot.config import SNAPSHOT, settings
from fpacopilot.warehouse import connect


def setup(title: str) -> None:
    st.set_page_config(page_title=f"FP&A copilot - {title}", page_icon=":material/query_stats:", layout="wide")


@st.cache_resource(show_spinner="Loading the star schema...")
def con():
    return connect()


@st.cache_data
def actuals_budget(start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    return v.actuals(con(), start, end), v.budget(con(), start, end)


def ytd() -> tuple[pd.DataFrame, pd.DataFrame]:
    s = settings()
    return actuals_budget(f"{s['budget_year']}-01-01", s["close_date"])


@st.cache_data
def forecast() -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    summary = json.loads((SNAPSHOT / "forecast_summary.json").read_text())
    return (summary, pd.read_parquet(SNAPSHOT / "forecast_backtest.parquet"),
            pd.read_parquet(SNAPSHOT / "forecast_december.parquet"))


@st.cache_data
def commentary() -> tuple[dict, dict]:
    from fpacopilot.commentary import facts, get

    f = facts()
    return f, get(f)


def gbp(x: float) -> str:
    sign, x = ("-" if x < 0 else ""), abs(x)
    return f"{sign}£{x / 1e6:,.2f}m" if x >= 1e6 else f"{sign}£{x / 1e3:,.0f}k"


def footer() -> None:
    s = settings()
    st.space("medium")
    st.caption(s["disclaimer"])
    st.caption(f"Source: {s['source']['citation']} Licence {s['source']['licence']}.")
