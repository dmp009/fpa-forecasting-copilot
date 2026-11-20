"""Method, budget assumptions and limits."""
import streamlit as st

from app.common import footer, setup
from fpacopilot.config import budget_drivers

setup("About")
st.title("About", icon=":material/info:")
d = budget_drivers()
st.markdown(f"""
**The business problem.** Every month, an FP&A team has a few days to explain why revenue is off budget and where
the year will land. Most of that time goes into rebuilding the same bridge and writing the same commentary.

**Data.** Real transactions of a UK online gift and homeware retailer (UCI Online Retail II, December 2009 to
December 2011, about one million invoice lines, GBP).

**Why 2011?** Data availability. Real sales at transaction level (each invoice line with product, quantity, price and
country) are rarely published, and UCI Online Retail II, the standard open dataset of this kind, ends in December 2011.
More recent public data is aggregated or synthetic. The method applies unchanged to current data. The data is cleaned (duplicates, cancellations, fees) and
loaded into a star schema (DuckDB), the same model that is exported to Power BI.

**Budget.** No company publishes its internal budget, so the FY2011 budget is built driver-based from FY2010 actuals:
- units: FY2010 same-month units x (1 + regional volume growth: UK {d['volume_growth']['UK']:.0%}, Europe
  {d['volume_growth']['Europe']:.0%}, Rest of world {d['volume_growth']['Rest of world']:.0%}), with category overrides;
- price: FY2010 average price by region and category, +{d['price_increase']:.0%};
- returns and shipping: FY2010 ratios by region.

**Bridge.** Volume, mix and price follow the standard FP&A definitions; they add up to the variance exactly (tested).

**Forecast.** Seasonal naive, an FP&A run-rate and gradient boosting, backtested month by month (WAPE). The best
method gives December; the landing is January-November actual + December forecast.

**Limits.** One retailer, two years; the budget is constructed, not the company's own; categories come from keywords
in product descriptions (about 92% of sales classified); the commentary is a draft for an analyst to review.
""")
footer()
