"""Driver-based FY2011 budget, built only from FY2010 actuals and config/budget.yaml.

Grain: month x region x category for product sales; month x region for returns and shipping.
- units   = FY2010 units of the same month x (1 + region volume growth + category override)
- price   = FY2010 average price of the region x category x (1 + list-price increase)
- returns = FY2010 return rate of the region (returns / product sales) x budget product sales
- shipping = FY2010 shipping income / product sales of the region x budget product sales
"""
from __future__ import annotations

import pandas as pd

from fpacopilot.config import budget_drivers, settings


def build_budget(lines: pd.DataFrame, drivers: dict | None = None) -> pd.DataFrame:
    drivers = drivers or budget_drivers()
    s = settings()
    base, year = s["base_year"], s["budget_year"]
    py = lines[lines["date"].dt.year == base].assign(month=lambda d: d["date"].dt.month)
    prod = py[py["line_type"] == "product"]

    monthly = prod.groupby(["month", "region", "category"], as_index=False).agg(
        py_units=("quantity", "sum"), py_revenue=("revenue", "sum"))
    annual = prod.groupby(["region", "category"]).agg(u=("quantity", "sum"), r=("revenue", "sum"))
    price = (annual["r"] / annual["u"]).rename("py_price").reset_index()
    b = monthly.merge(price, on=["region", "category"])
    growth = b["region"].map(drivers["volume_growth"]) + b["category"].map(
        drivers.get("category_volume_overrides", {})).fillna(0.0)
    b["units"] = b["py_units"] * (1 + growth)
    b["price"] = b["py_price"] * (1 + drivers["price_increase"])
    b["revenue"] = b["units"] * b["price"]
    b["line_type"] = "product"

    by_region = py.groupby(["region", "line_type"])["revenue"].sum().unstack(fill_value=0.0)
    ratios = {lt: by_region[lt] / by_region["product"] for lt in ("return", "shipping")}
    sales_rm = b.groupby(["month", "region"], as_index=False)["revenue"].sum()
    extra = [sales_rm.assign(line_type=lt, category="Non-product", units=0.0, price=0.0,
                             revenue=sales_rm["revenue"] * sales_rm["region"].map(r))
             for lt, r in ratios.items()]

    out = pd.concat([b, *extra], ignore_index=True)
    out["month_start"] = pd.to_datetime({"year": year, "month": out["month"], "day": 1})
    return out[["month_start", "region", "category", "line_type", "units", "price", "revenue"]]
