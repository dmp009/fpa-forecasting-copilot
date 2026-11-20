"""Turn raw invoice lines into classified, de-duplicated lines with a P&L line, region and category.

Rules (each one is counted in data_quality_report.md):
- exact duplicate rows are dropped (the same line scanned twice);
- a product is a StockCode of five digits with an optional letter suffix (e.g. 85123A);
- postage codes (POST, DOT, C2) are shipping income;
- everything else (Amazon fees, bank charges, manual adjustments, bad-debt write-offs, tests) is
  "other" and stays out of net revenue;
- product lines with a zero or negative price are stock adjustments, not sales, and are dropped;
- an invoice starting with "C" is a cancellation: product lines on it are returns.
"""
from __future__ import annotations

import re

import pandas as pd

from fpacopilot.config import categories, settings

PRODUCT = re.compile(r"^\d{5}[A-Za-z]{0,2}$")
SHIPPING = {"POST", "DOT", "C2"}


def category_of(description: str | None, rules: dict | None = None) -> str:
    rules = rules or categories()
    words = set(re.findall(r"[A-Z'\-]+", str(description or "").upper()))
    for cat in rules["order"]:
        if words & set(cat["words"]):
            return cat["name"]
    return rules["other"]


def region_of(country: str) -> str:
    return settings()["regions"].get(country, "Rest of world")


def classify(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Returns (clean lines, counts of what each rule removed or reclassified)."""
    df = raw.rename(columns={"Customer ID": "customer_id", "InvoiceDate": "ts", "StockCode": "stock_code",
                             "Invoice": "invoice", "Description": "description", "Quantity": "quantity",
                             "Price": "price", "Country": "country"})
    counts = {"raw_rows": len(df)}
    df = df.drop_duplicates()
    counts["duplicates_dropped"] = counts["raw_rows"] - len(df)

    code = df["stock_code"].astype(str).str.strip()
    is_product = code.str.match(PRODUCT)
    df = df.assign(
        line_type=is_product.map({True: "product", False: "other"}).where(~code.isin(SHIPPING), "shipping"),
        cancelled=df["invoice"].str.startswith("C"),
    )
    bad_price = (df["line_type"] == "product") & (df["price"] <= 0)
    counts["zero_price_product_lines_dropped"] = int(bad_price.sum())
    df = df[~bad_price].copy()

    df.loc[(df["line_type"] == "product") & df["cancelled"], "line_type"] = "return"
    df["revenue"] = df["quantity"] * df["price"]
    df["date"] = df["ts"].dt.normalize()
    df["region"] = df["country"].map(region_of)
    # one description per code (the most frequent), so a product never sits in two categories
    desc = (df[df["line_type"].isin(["product", "return"])].groupby("stock_code")["description"]
            .agg(lambda s: s.mode().iat[0] if s.notna().any() else None))
    rules = categories()
    cat = {c: category_of(d, rules) for c, d in desc.items()}
    df["category"] = df["stock_code"].map(cat).fillna("Non-product")
    df["customer_id"] = df["customer_id"].astype("Int64")
    counts.update({f"lines_{k}": int(v) for k, v in df["line_type"].value_counts().items()})
    counts["clean_rows"] = len(df)
    return df.reset_index(drop=True), counts
