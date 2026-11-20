"""Export the star schema as CSV for Power BI (powerbi/data/, git-ignored: run `make powerbi`).

The model, the relationships and the DAX measures are in powerbi/README.md and powerbi/measures.dax.
fact_budget is at month grain, so Power BI relates it to dim_date through month_start (the first day
of the month) and to products and markets only through category and region (dim_category and dim_region).
"""
from __future__ import annotations

from fpacopilot.config import POWERBI
from fpacopilot.warehouse import TABLES, connect


def export() -> dict[str, int]:
    out = POWERBI / "data"
    out.mkdir(parents=True, exist_ok=True)
    con = connect()
    rows = {}
    extra = {"dim_category": "SELECT DISTINCT category FROM dim_product ORDER BY 1",
             "dim_region": "SELECT DISTINCT region FROM dim_market ORDER BY 1"}
    for t in (*TABLES, *extra):
        df = con.execute(extra.get(t, f"SELECT * FROM {t}")).df()
        df.to_csv(out / f"{t}.csv", index=False, date_format="%Y-%m-%d")
        rows[t] = len(df)
    print(rows)
    return rows
