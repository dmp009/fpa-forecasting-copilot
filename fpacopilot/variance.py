"""Budget vs actual and the price / volume / mix bridge.

For product sales over a period, with segments i = region x category, units u and price p = revenue/u:
    volume = (U_act - U_bud) x P_bud               P = total revenue / total units
    mix    = sum_i U_act x (w_act,i - w_bud,i) x p_bud,i     w = segment share of units
    price  = sum_i u_act,i x (p_act,i - p_bud,i)
volume + mix + price = product revenue actual - budget, exactly (tested). Returns and shipping are
added as their own bridge steps, so the bridge ends at net revenue.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

SEG = ["region", "category"]


def actuals(con, start: str, end: str) -> pd.DataFrame:
    return con.execute("""
        SELECT month_start, region, category, line_type, sum(units) AS units, sum(revenue) AS revenue
        FROM v_sales WHERE date BETWEEN ? AND ? AND line_type IN ('product', 'return', 'shipping')
        GROUP BY ALL
    """, [start, end]).df()


def budget(con, start: str, end: str) -> pd.DataFrame:
    return con.execute("""
        SELECT month_start, region, category, line_type, sum(units) AS units, sum(revenue) AS revenue
        FROM fact_budget WHERE month_start BETWEEN date_trunc('month', CAST(? AS DATE)) AND ?
        GROUP BY ALL
    """, [start, end]).df()


@dataclass(frozen=True)
class Bridge:
    budget_net: float
    volume: float
    mix: float
    price: float
    returns: float
    shipping: float
    actual_net: float

    def steps(self) -> list[tuple[str, float]]:
        return [("Budget", self.budget_net), ("Volume", self.volume), ("Mix", self.mix), ("Price", self.price),
                ("Returns", self.returns), ("Shipping", self.shipping), ("Actual", self.actual_net)]

    def as_dict(self) -> dict:
        return asdict(self)


def pvm(act: pd.DataFrame, bud: pd.DataFrame) -> pd.DataFrame:
    """Per-segment volume, mix and price effects for product sales (columns sum to the total variance)."""
    a = act[act["line_type"] == "product"].groupby(SEG)[["units", "revenue"]].sum()
    b = bud[bud["line_type"] == "product"].groupby(SEG)[["units", "revenue"]].sum()
    df = a.merge(b, left_index=True, right_index=True, how="outer", suffixes=("_act", "_bud")).fillna(0.0)
    p_bud = (df["revenue_bud"] / df["units_bud"]).where(df["units_bud"] > 0)
    p_act = (df["revenue_act"] / df["units_act"]).where(df["units_act"] > 0)
    # a segment with no budget is priced at its actual price: its whole revenue lands in mix
    p_bud = p_bud.fillna(p_act).fillna(0.0)
    U_act, U_bud = df["units_act"].sum(), df["units_bud"].sum()
    P_bud = df["revenue_bud"].sum() / U_bud
    w_act, w_bud = df["units_act"] / U_act, df["units_bud"] / U_bud
    df["volume"] = (U_act - U_bud) * w_bud * P_bud
    df["mix"] = U_act * (w_act - w_bud) * p_bud
    df["price"] = df["units_act"] * (p_act.fillna(0.0) - p_bud)
    df["variance"] = df["revenue_act"] - df["revenue_bud"]
    return df.reset_index()


def bridge(act: pd.DataFrame, bud: pd.DataFrame) -> Bridge:
    seg = pvm(act, bud)

    def line(df, lt):
        return float(df.loc[df["line_type"] == lt, "revenue"].sum())

    return Bridge(
        budget_net=sum(line(bud, lt) for lt in ("product", "return", "shipping")),
        volume=float(seg["volume"].sum()), mix=float(seg["mix"].sum()), price=float(seg["price"].sum()),
        returns=line(act, "return") - line(bud, "return"), shipping=line(act, "shipping") - line(bud, "shipping"),
        actual_net=sum(line(act, lt) for lt in ("product", "return", "shipping")),
    )


def pnl(act: pd.DataFrame, bud: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    """Revenue P&L (product sales, returns, net product sales, shipping, net revenue): actual, budget,
    variance and variance %, optionally split by a column (region or category)."""
    keys = [by] if by else []

    def lines(df):
        t = df.pivot_table(index=keys or None, columns="line_type", values="revenue", aggfunc="sum", fill_value=0.0)
        if not keys:
            t = t.sum().to_frame().T
        for col in ("product", "return", "shipping"):
            if col not in t:
                t[col] = 0.0
        t["net_product"] = t["product"] + t["return"]
        t["net_revenue"] = t["net_product"] + t["shipping"]
        return t[["product", "return", "net_product", "shipping", "net_revenue"]]

    a, b = lines(act), lines(bud)
    out = pd.concat({"actual": a, "budget": b}, axis=1).fillna(0.0)
    for c in a.columns:
        out[("variance", c)] = out[("actual", c)] - out[("budget", c)]
        out[("variance_pct", c)] = out[("variance", c)] / out[("budget", c)].abs().where(out[("budget", c)] != 0)
    return out
