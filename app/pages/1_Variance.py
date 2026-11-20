"""Budget vs actual and the price / volume / mix bridge."""
import pandas as pd
import streamlit as st

from app import charts
from app.common import footer, gbp, setup, ytd
from fpacopilot import variance as v

setup("Variance")
st.title("Variance", icon=":material/waterfall_chart:")
act, bud = ytd()

regions = sorted(act["region"].unique())
pick = st.segmented_control("Region", ["All", *regions], default="All")
if pick and pick != "All":
    act, bud = act[act["region"] == pick], bud[bud["region"] == pick]

br = v.bridge(act, bud)
st.markdown(
    f"Year to date (January to November 2011), net revenue is **{gbp(br.actual_net)}** against a budget of "
    f"**{gbp(br.budget_net)}**: **{gbp(br.actual_net - br.budget_net)}** "
    f"({br.actual_net / br.budget_net - 1:+.1%})."
)
st.plotly_chart(charts.bridge(br.steps(), "Budget to actual, net revenue YTD"), width="stretch")
st.caption(
    "**Volume**: more or fewer units than budgeted, at the average budget price. **Mix**: units moving between "
    "region x category segments with different prices. **Price**: actual vs budget price on the units sold. "
    "Returns and shipping income are their own steps. The steps add up exactly to the variance."
)

def by_month(df: pd.DataFrame) -> pd.Series:
    return df.groupby("month_start")["revenue"].sum()

m = pd.DataFrame({"actual": by_month(act), "budget": by_month(bud)}).reset_index()
st.plotly_chart(charts.monthly_vs_budget(m, "Net revenue by month"), width="stretch")

c1, c2 = st.columns(2)
seg = v.pvm(act, bud)
cat = seg.groupby("category", as_index=False)[["variance", "volume", "mix", "price"]].sum()
c1.plotly_chart(charts.variance_bars(cat, "category", "Product sales variance by category"), width="stretch")
if not pick or pick == "All":
    reg = seg.groupby("region", as_index=False)[["variance"]].sum()
    c2.plotly_chart(charts.variance_bars(reg, "region", "Product sales variance by region"), width="stretch")

st.subheader("Revenue P&L")
p = v.pnl(act, bud, "region" if not pick or pick == "All" else None)
lines = {"product": "Product sales", "return": "Returns", "net_product": "Net product sales",
         "shipping": "Shipping income", "net_revenue": "Net revenue"}
rows = []
for key, name in lines.items():
    for idx in p.index:
        rows.append({"Line": name, "Region": idx if isinstance(idx, str) else "All",
                     "Actual": p.loc[idx, ("actual", key)], "Budget": p.loc[idx, ("budget", key)],
                     "Variance": p.loc[idx, ("variance", key)], "Variance %": p.loc[idx, ("variance_pct", key)]})
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", column_config={
    "Actual": st.column_config.NumberColumn(format="£%,.0f"), "Budget": st.column_config.NumberColumn(format="£%,.0f"),
    "Variance": st.column_config.NumberColumn(format="£%,.0f"), "Variance %": st.column_config.NumberColumn(format="percent"),
})

with st.expander("Category detail: volume, mix and price"):
    st.dataframe(cat.sort_values("variance"), hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="£%,.0f") for c in ["variance", "volume", "mix", "price"]})
footer()
