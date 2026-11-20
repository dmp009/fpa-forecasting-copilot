"""Backtest of three forecasting methods and the FY2011 landing."""
import pandas as pd
import streamlit as st

from app import charts
from app.common import footer, forecast, gbp, setup
from fpacopilot.forecast import LABELS, METHODS

setup("Forecast & landing")
st.title("Forecast & landing", icon=":material/trending_up:")
summary, bt, dec = forecast()
land, scores = summary["landing"], pd.DataFrame(summary["scores"])
best = land["best_method"]

c1, c2, c3 = st.columns(3, border=True)
c1.metric("December forecast", gbp(land["december_forecast"]), f"{land['december_forecast'] / land['december_budget'] - 1:+.1%} vs budget")
c2.metric("Full-year landing", gbp(land["full_year_landing"]))
c3.metric("Full-year budget", gbp(land["full_year_budget"]),
          f"{land['full_year_landing'] / land['full_year_budget'] - 1:+.1%} landing vs budget", delta_color="off")

st.plotly_chart(charts.landing(land["ytd_actual"], land["december_forecast"], land["full_year_budget"],
                               "FY2011: Jan-Nov actual + December forecast vs budget"), width="stretch")

st.subheader("Which method to trust: the backtest")
st.markdown(
    "Each method forecast every month from January to November 2011 using only data available at the previous "
    f"month-end. The error is **WAPE** (total absolute error / total actual; lower is better). "
    f"**{LABELS[best]}** had the lowest error, so it gives the December forecast."
)
tot = bt.groupby("month", as_index=False)[[*METHODS, "actual"]].sum()
st.plotly_chart(charts.backtest(tot, LABELS, "Monthly net revenue: actual vs each method's forecast"), width="stretch")
table = scores.rename(columns=LABELS).loc[["Total", "UK", "Europe", "Rest of world"]]
st.dataframe(table, width="stretch", column_config={c: st.column_config.NumberColumn(format="percent") for c in table.columns})
st.info(
    "The machine-learning model does **not** win. With two years of history, one December to learn from and a "
    "business that grew unevenly by region, last year's same month is a hard benchmark to beat. Reporting this "
    "honestly is the point of a backtest: the model is kept as a challenger and re-tested every month.",
    icon=":material/lightbulb:",
)

st.subheader("Early check on December")
st.markdown(
    f"The data ends on **{land['partial_through']}**. Over those days, actual net revenue was "
    f"**{gbp(land['december_partial_actual'])}** against **{gbp(land['december_partial_forecast'])}** expected from the "
    "forecast (spread by last December's daily pattern)."
)
st.dataframe(dec.rename(columns=LABELS), hide_index=True, width="stretch",
             column_config={LABELS[m]: st.column_config.NumberColumn(format="£%,.0f") for m in METHODS})
footer()
