"""Star schema: three dimensions and three facts, saved as parquet in data/snapshot/ and queried
with DuckDB. The same tables are exported as CSV for Power BI (powerbi/).

dim_date      one row per calendar day, Dec 2009 to Dec 2011
dim_product   one row per stock code (description, category)
dim_market    one row per country (region)
fact_sales    day x stock code x country x P&L line: units, revenue (the actuals)
fact_invoices one row per invoice: day, country, customer, units, revenue (orders, customers, AOV)
fact_budget   month x region x category x P&L line: units, revenue (the FY2011 budget)
"""
from __future__ import annotations

import duckdb
import pandas as pd

from fpacopilot.config import SNAPSHOT

TABLES = ("dim_date", "dim_product", "dim_market", "fact_sales", "fact_invoices", "fact_budget")


def dim_date(start: str, end: str) -> pd.DataFrame:
    d = pd.date_range(start, end, freq="D")
    return pd.DataFrame({
        "date": d, "year": d.year, "quarter": d.quarter, "month": d.month,
        "month_start": d.to_period("M").to_timestamp(), "month_name": d.strftime("%b"),
        "iso_week": d.isocalendar().week.to_numpy(), "weekday": d.dayofweek, "is_weekend": d.dayofweek >= 5,
    })


def build(lines: pd.DataFrame, budget: pd.DataFrame) -> dict[str, pd.DataFrame]:
    sales = (lines.groupby(["date", "stock_code", "country", "line_type"], as_index=False)
             .agg(units=("quantity", "sum"), revenue=("revenue", "sum"), lines=("revenue", "size")))
    goods = lines[lines["line_type"].isin(["product", "return"])]
    invoices = (goods.groupby("invoice", as_index=False)
                .agg(date=("date", "first"), country=("country", "first"), customer_id=("customer_id", "first"),
                     cancelled=("cancelled", "first"), units=("quantity", "sum"), revenue=("revenue", "sum")))
    product = (lines.sort_values("ts").groupby("stock_code", as_index=False)
               .agg(description=("description", "last"), category=("category", "first")))
    market = lines[["country", "region"]].drop_duplicates().sort_values("country").reset_index(drop=True)
    return {
        "dim_date": dim_date(lines["date"].min(), lines["date"].max()),
        "dim_product": product, "dim_market": market, "fact_sales": sales, "fact_invoices": invoices,
        "fact_budget": budget,
    }


def save(tables: dict[str, pd.DataFrame]) -> None:
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_parquet(SNAPSHOT / f"{name}.parquet", index=False)


def connect(snapshot=SNAPSHOT) -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with one view per parquet table plus `v_sales` (facts joined to dimensions)."""
    con = duckdb.connect()
    for t in TABLES:
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_parquet('{snapshot / (t + '.parquet')}')")
    con.execute("""
        CREATE VIEW v_sales AS
        SELECT s.*, d.year, d.month, d.month_start, p.category, m.region
        FROM fact_sales s
        JOIN dim_date d USING (date)
        JOIN dim_product p USING (stock_code)
        JOIN dim_market m USING (country)
    """)
    return con
