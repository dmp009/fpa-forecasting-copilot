"""Data-quality checks (pandera schemas + reconciliations) and data_quality_report.md."""
from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

from fpacopilot.config import ROOT, settings

LINE_TYPES = ["product", "return", "shipping", "other"]

SCHEMAS = {
    "fact_sales": pa.DataFrameSchema({
        "date": pa.Column("datetime64[us]"),
        "stock_code": pa.Column(str, nullable=False),
        "country": pa.Column(str, nullable=False),
        "line_type": pa.Column(str, pa.Check.isin(LINE_TYPES)),
        "units": pa.Column(int),
        "revenue": pa.Column(float),
        "lines": pa.Column(int, pa.Check.ge(1)),
    }, unique=["date", "stock_code", "country", "line_type"]),
    "fact_budget": pa.DataFrameSchema({
        "month_start": pa.Column("datetime64[us]"),
        "region": pa.Column(str, pa.Check.isin(["UK", "Europe", "Rest of world"])),
        "line_type": pa.Column(str, pa.Check.isin(["product", "return", "shipping"])),
        "units": pa.Column(float, pa.Check.ge(0)),
        "revenue": pa.Column(float),
    }, unique=["month_start", "region", "category", "line_type"]),
    "dim_product": pa.DataFrameSchema({"stock_code": pa.Column(str, unique=True)}),
    "dim_market": pa.DataFrameSchema({"country": pa.Column(str, unique=True)}),
}


def checks(tables: dict[str, pd.DataFrame], counts: dict) -> list[tuple[str, bool, str]]:
    """(check, passed, detail) rows. Schema failures raise: a broken snapshot must not be saved silently."""
    for name, schema in SCHEMAS.items():
        schema.validate(tables[name], lazy=True)
    sales, inv, bud = tables["fact_sales"], tables["fact_invoices"], tables["fact_budget"]
    goods = sales[sales["line_type"].isin(["product", "return"])]
    prod = sales[sales["line_type"] == "product"]
    known = set(tables["dim_product"]["stock_code"])
    out = [
        ("Every fact row has a product in dim_product", set(sales["stock_code"]) <= known, ""),
        ("Every fact row has a market in dim_market", set(sales["country"]) <= set(tables["dim_market"]["country"]), ""),
        ("Invoice table reconciles to product + return revenue",
         abs(inv["revenue"].sum() - goods["revenue"].sum()) < 0.01,
         f"{inv['revenue'].sum():,.2f} vs {goods['revenue'].sum():,.2f}"),
        ("Budget covers 12 months x 3 regions", bud["month_start"].nunique() == 12 and bud["region"].nunique() == 3, ""),
        ("Returns are negative revenue", (sales.loc[sales["line_type"] == "return", "revenue"] <= 0).all(), ""),
    ]
    cat_share = 1 - prod.loc[prod["stock_code"].map(
        tables["dim_product"].set_index("stock_code")["category"]) == "Accessories & other", "revenue"].sum() / prod[
        "revenue"].sum()
    out.append(("Keyword categories cover at least 85% of product sales", cat_share >= 0.85, f"{cat_share:.1%}"))
    return out


def report(tables: dict[str, pd.DataFrame], counts: dict) -> str:
    rows = checks(tables, counts)
    s = settings()
    md = [
        "# Data quality report", "",
        f"Source: {s['source']['citation']} Licence {s['source']['licence']}.", "",
        "## Cleaning", "", "| Step | Rows |", "|---|---:|",
        *[f"| {k.replace('_', ' ')} | {v:,} |" for k, v in counts.items()], "",
        "## Checks", "", "| Check | Result | Detail |", "|---|---|---|",
        *[f"| {c} | {'pass' if ok else 'FAIL'} | {d} |" for c, ok, d in rows], "",
        "Schemas (types, allowed values, unique keys) are validated with pandera before the snapshot is saved.",
        "",
    ]
    text = "\n".join(md)
    (ROOT / "data_quality_report.md").write_text(text, encoding="utf-8")
    failed = [c for c, ok, _ in rows if not ok]
    if failed:
        raise ValueError(f"data-quality checks failed: {failed}")
    return text
