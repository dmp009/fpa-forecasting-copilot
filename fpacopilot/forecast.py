"""Next-month net revenue forecast by region, a monthly backtest, and the FY2011 landing.

Three methods, each forecasting month M from the close of month M-1 (no data from M is used):
- seasonal naive: the same month last year;
- run-rate: the same month last year x the year-on-year growth of the last three closed months,
  which is how many FP&A teams roll a forecast forward;
- gradient boosting: a scikit-learn HistGradientBoostingRegressor on daily revenue. The target is
  daily revenue divided by the region's average of the 28 days before the forecast origin, so one
  model learns the weekday, month-of-year and pre-Christmas shape across regions and sizes; the
  daily forecasts are summed to the month.
Backtest: every month from January to November 2011. Metric: WAPE (sum |error| / sum actual).
The method with the lowest backtest WAPE gives the December forecast used in the landing.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from fpacopilot.config import SNAPSHOT, settings
from fpacopilot.warehouse import connect

REGIONS = ["UK", "Europe", "Rest of world"]
METHODS = ["seasonal_naive", "run_rate", "gradient_boosting"]
LABELS = {"seasonal_naive": "Seasonal naive", "run_rate": "Run-rate (FP&A)", "gradient_boosting": "Gradient boosting"}


def daily(con) -> pd.DataFrame:
    """Daily net revenue (product + returns + shipping) per region; days with no invoice are 0."""
    d = con.execute("""
        SELECT date, region, sum(revenue) AS revenue FROM v_sales
        WHERE line_type IN ('product', 'return', 'shipping') GROUP BY ALL
    """).df()
    full = pd.MultiIndex.from_product([pd.date_range(d["date"].min(), d["date"].max()), REGIONS],
                                      names=["date", "region"])
    return d.set_index(["date", "region"])["revenue"].reindex(full, fill_value=0.0).reset_index()


def monthly(day: pd.DataFrame) -> pd.Series:
    return day.assign(month=day["date"].dt.to_period("M")).groupby(["region", "month"])["revenue"].sum()


def seasonal_naive(m: pd.Series, region: str, month: pd.Period) -> float:
    return float(m.get((region, month - 12), np.nan))


def run_rate(m: pd.Series, region: str, month: pd.Period) -> float:
    # only months that exist in both years count (the data starts in December 2009)
    last3 = [month - k for k in (1, 2, 3) if (region, month - k - 12) in m.index and (region, month - k) in m.index]
    now = sum(m[(region, p)] for p in last3)
    ly = sum(m[(region, p - 12)] for p in last3)
    return float(m.get((region, month - 12), np.nan) * (now / ly if ly else 1.0))


def features(dates: pd.DatetimeIndex, region: str) -> pd.DataFrame:
    xmas = pd.to_datetime(dates.year.astype(str) + "-12-25")
    return pd.DataFrame({
        "region": REGIONS.index(region), "weekday": dates.day_of_week, "day": dates.day, "month": dates.month,
        "days_to_christmas": np.clip((xmas - dates).days.to_numpy(), -10, None),
    }, index=dates)


def _training_set(day: pd.DataFrame, origin: pd.Timestamp) -> tuple[pd.DataFrame, np.ndarray]:
    """Rows: every day before the origin, scaled by the 28-day level before its own month start."""
    X, y = [], []
    for region in REGIONS:
        s = day[day["region"] == region].set_index("date")["revenue"]
        s = s[s.index <= origin]
        starts = s.index.to_period("M").to_timestamp()
        level = {m: s[(s.index < m) & (s.index >= m - pd.Timedelta(days=28))].mean() for m in starts.unique()}
        lv = pd.Series(starts.map(level), index=s.index)
        ok = lv.notna() & (lv > 0)
        X.append(features(s.index[ok], region))
        y.append((s[ok] / lv[ok]).to_numpy())
    return pd.concat(X), np.concatenate(y)


def gradient_boosting(day: pd.DataFrame, month: pd.Period, models: dict | None = None) -> dict[str, float]:
    origin = month.to_timestamp() - pd.Timedelta(days=1)
    key = str(month)
    if models is not None and key in models:
        model = models[key]
    else:
        X, y = _training_set(day, origin)
        model = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
                                              categorical_features=[0], random_state=0).fit(X, y)
        if models is not None:
            models[key] = model
    days = pd.date_range(month.to_timestamp(), month.to_timestamp(how="end").normalize())
    out = {}
    for region in REGIONS:
        s = day[day["region"] == region].set_index("date")["revenue"]
        level = s[(s.index <= origin) & (s.index > origin - pd.Timedelta(days=28))].mean()
        out[region] = float(np.clip(model.predict(features(days, region)), 0, None).sum() * level)
    return out


def predict(day: pd.DataFrame, month: pd.Period) -> pd.DataFrame:
    m = monthly(day[day["date"] < month.to_timestamp()])
    gb = gradient_boosting(day, month)
    return pd.DataFrame([
        {"region": r, "month": str(month), "seasonal_naive": seasonal_naive(m, r, month),
         "run_rate": run_rate(m, r, month), "gradient_boosting": gb[r]} for r in REGIONS])


def wape(actual: pd.Series, fc: pd.Series) -> float:
    return float((actual - fc).abs().sum() / actual.abs().sum())


@dataclass(frozen=True)
class Landing:
    best_method: str
    december_forecast: float
    ytd_actual: float
    full_year_landing: float
    full_year_budget: float
    december_budget: float
    december_partial_actual: float
    december_partial_forecast: float
    partial_through: str


def backtest(day: pd.DataFrame, months: list[pd.Period]) -> pd.DataFrame:
    m = monthly(day)
    rows = [predict(day, mo) for mo in months]
    bt = pd.concat(rows, ignore_index=True)
    bt["actual"] = [m[(r, pd.Period(mo, "M"))] for r, mo in zip(bt["region"], bt["month"], strict=True)]
    return bt


def scores(bt: pd.DataFrame) -> pd.DataFrame:
    tot = bt.groupby("month")[[*METHODS, "actual"]].sum().assign(region="Total").reset_index()
    both = pd.concat([bt, tot], ignore_index=True)
    return pd.DataFrame({meth: both.groupby("region").apply(lambda g, mm=meth: wape(g["actual"], g[mm]))
                         for meth in METHODS})


def run() -> dict:
    s = settings()
    con = connect()
    day = daily(con)
    year = s["budget_year"]
    months = [pd.Period(f"{year}-{k:02d}", "M") for k in range(1, 12)]
    bt = backtest(day, months)
    sc = scores(bt)
    best = sc.loc["Total"].idxmin()

    dec = pd.Period(s["landing_month"], "M")
    fc = predict(day, dec)
    gb_days = _daily_partial(day, dec, best, fc)
    budget = con.execute("SELECT month_start, sum(revenue) AS r FROM fact_budget GROUP BY ALL").df()
    ytd = float(monthly(day).loc[:, [mo for mo in months]].sum())
    landing = Landing(
        best_method=best, december_forecast=float(fc[best].sum()), ytd_actual=ytd,
        full_year_landing=ytd + float(fc[best].sum()), full_year_budget=float(budget["r"].sum()),
        december_budget=float(budget.loc[budget["month_start"].dt.month == 12, "r"].sum()), **gb_days,
    )
    bt.to_parquet(SNAPSHOT / "forecast_backtest.parquet", index=False)
    fc.to_parquet(SNAPSHOT / "forecast_december.parquet", index=False)
    out = {"scores": sc.round(4).to_dict(), "landing": landing.__dict__}
    (SNAPSHOT / "forecast_summary.json").write_text(json.dumps(out, indent=2, default=float))
    print(sc.round(3))
    print(json.dumps(landing.__dict__, indent=2, default=float))
    return out


def _daily_partial(day: pd.DataFrame, month: pd.Period, best: str, fc: pd.DataFrame) -> dict:
    """The data stops part-way through December: compare actual and forecast over those days only,
    spreading the monthly forecast by last December's daily pattern."""
    last = day["date"].max()
    days_act = day[(day["date"] >= month.to_timestamp()) & (day["date"] <= last)]
    ly = day[(day["date"].dt.to_period("M") == month - 12)]
    share = ly[ly["date"].dt.day <= last.day]["revenue"].sum() / ly["revenue"].sum()
    return {"december_partial_actual": float(days_act["revenue"].sum()),
            "december_partial_forecast": float(fc[best].sum() * share), "partial_through": str(last.date())}


if __name__ == "__main__":
    run()
