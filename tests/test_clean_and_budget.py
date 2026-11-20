import pandas as pd
import pytest

from fpacopilot.budget import build_budget
from fpacopilot.clean import category_of, classify, region_of


def raw(rows):
    return pd.DataFrame(rows, columns=["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price",
                                       "Customer ID", "Country"]).assign(InvoiceDate=lambda d: pd.to_datetime(d["InvoiceDate"]))


def test_classify_rules():
    r = raw([
        ("1", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 6, "2010-01-04 10:00", 2.55, 1, "United Kingdom"),
        ("1", "85123A", "WHITE HANGING HEART T-LIGHT HOLDER", 6, "2010-01-04 10:00", 2.55, 1, "United Kingdom"),  # dup
        ("2", "22423", "REGENCY CAKESTAND 3 TIER", 1, "2010-01-05 10:00", 12.75, 2, "France"),
        ("2", "POST", "POSTAGE", 1, "2010-01-05 10:00", 18.0, 2, "France"),
        ("3", "AMAZONFEE", "AMAZON FEE", 1, "2010-01-06 10:00", 100.0, None, "United Kingdom"),
        ("4", "22423", "REGENCY CAKESTAND 3 TIER", 5, "2010-01-06 10:00", 0.0, None, "United Kingdom"),  # zero price
        ("C5", "22423", "REGENCY CAKESTAND 3 TIER", -1, "2010-01-07 10:00", 12.75, 2, "Japan"),
    ])
    df, counts = classify(r)
    assert counts["duplicates_dropped"] == 1
    assert counts["zero_price_product_lines_dropped"] == 1
    assert list(df["line_type"]) == ["product", "product", "shipping", "other", "return"]
    assert list(df["region"]) == ["UK", "Europe", "Europe", "UK", "Rest of world"]
    assert df.loc[df["line_type"] == "return", "revenue"].iloc[0] == pytest.approx(-12.75)
    assert df.loc[df["stock_code"] == "POST", "category"].iloc[0] == "Non-product"


def test_category_and_region():
    assert category_of("WHITE HANGING HEART T-LIGHT HOLDER") == "Lighting & candles"
    assert category_of("SOMETHING UNKNOWN") == "Accessories & other"
    assert region_of("EIRE") == "Europe" and region_of("Australia") == "Rest of world"


def test_budget_drivers():
    lines = pd.DataFrame({
        "date": pd.to_datetime(["2010-03-10", "2010-03-12", "2010-03-12", "2010-03-12", "2009-12-05"]),
        "region": ["UK", "UK", "UK", "UK", "UK"], "category": ["A", "A", "Non-product", "Non-product", "A"],
        "line_type": ["product", "product", "return", "shipping", "product"],
        "quantity": [10, 30, -2, 1, 99], "revenue": [100.0, 300.0, -40.0, 20.0, 990.0],
    })
    drivers = {"volume_growth": {"UK": 0.10}, "price_increase": 0.05, "category_volume_overrides": {"A": -0.05}}
    b = build_budget(lines, drivers).set_index("line_type")
    assert b.loc["product", "units"] == pytest.approx(40 * 1.05)
    assert b.loc["product", "price"] == pytest.approx(10 * 1.05)
    sales = 40 * 1.05 * 10 * 1.05
    assert b.loc["product", "revenue"] == pytest.approx(sales)
    assert b.loc["return", "revenue"] == pytest.approx(sales * -0.1)
    assert b.loc["shipping", "revenue"] == pytest.approx(sales * 0.05)
    assert (b["month_start"] == pd.Timestamp("2011-03-01")).all()
