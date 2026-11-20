"""FP&A forecasting copilot: landing page."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.common import commentary, footer, gbp, setup, ytd
from fpacopilot import variance as v

setup("Home")
st.title("FP&A forecasting copilot", icon=":material/query_stats:")
st.markdown(
    "Month-end close for a UK online retailer of gifts and homeware: **budget vs actual**, a "
    "**price / volume / mix bridge** that explains the gap, a **December forecast** that gives the "
    "full-year landing, and a **variance commentary** whose every figure is checked against the numbers."
)
st.caption("Real sales from 2009-2011: the most recent open dataset with transaction-level sales and prices "
           "(see About). The method applies unchanged to current data.")

act, bud = ytd()
br = v.bridge(act, bud)
f, _ = commentary()
land = f["landing"]
c1, c2, c3, c4 = st.columns(4, border=True)
c1.metric("Net revenue YTD (Jan-Nov 2011)", gbp(br.actual_net))
c2.metric("Budget YTD", gbp(br.budget_net))
c3.metric("Variance YTD", gbp(br.actual_net - br.budget_net), f["ytd"]["variance_pct"])
c4.metric("Full-year landing", land["full_year_landing"], land["full_year_gap_pct"] + " vs budget")

st.subheader("Who it is for")
p1, p2, p3 = st.columns(3, border=True)
p1.markdown("**FP&A analyst**\n\nClose the month in minutes: the bridge, the P&L by region and the "
            "draft commentary are ready when the data lands.")
p2.markdown("**Finance director / CFO**\n\nSee in one page why revenue is off budget and where the "
            "year will land, with a recommended action.")
p3.markdown("**Commercial & category managers**\n\nSee which regions and categories drive the gap, "
            "split into volume, mix and price.")

st.subheader("Views")
v1, v2 = st.columns(2, border=True)
with v1:
    st.markdown("**Variance**. Budget vs actual by month, region and category, and the price / volume / mix bridge.")
    st.page_link("pages/1_Variance.py", label="Open Variance", icon=":material/waterfall_chart:")
    st.markdown("**Forecast & landing**. Three forecasting methods backtested month by month, and the full-year landing.")
    st.page_link("pages/2_Forecast_and_landing.py", label="Open Forecast & landing", icon=":material/trending_up:")
with v2:
    st.markdown("**Commentary**. The month-end variance commentary, with the facts it may use and the number check.")
    st.page_link("pages/3_Commentary.py", label="Open Commentary", icon=":material/edit_note:")
    st.markdown("**Data quality**. Cleaning steps, schema checks and reconciliations.")
    st.page_link("pages/4_Data_quality.py", label="Open Data quality", icon=":material/fact_check:")
st.markdown("The About page explains the method, the budget assumptions and the limits.")
footer()
