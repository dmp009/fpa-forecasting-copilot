import pandas as pd
import pytest

from fpacopilot.forecast import features, run_rate, seasonal_naive, wape


def series():
    idx = [("UK", pd.Period(f"{y}-{m:02d}", "M")) for y in (2010, 2011) for m in range(1, 13)]
    vals = [100.0] * 12 + [120.0] * 12
    return pd.Series(vals, index=pd.MultiIndex.from_tuples(idx))


def test_seasonal_naive_is_same_month_last_year():
    assert seasonal_naive(series(), "UK", pd.Period("2011-06", "M")) == 100.0


def test_run_rate_scales_by_last_three_months_growth():
    assert run_rate(series(), "UK", pd.Period("2011-06", "M")) == pytest.approx(100.0 * 1.2)


def test_run_rate_skips_months_without_a_prior_year():
    m = series().drop(("UK", pd.Period("2010-02", "M")))
    # Feb 2011 has no Feb 2010 to compare with: only Mar and Apr count, growth is still 1.2
    assert run_rate(m, "UK", pd.Period("2011-05", "M")) == pytest.approx(120.0)


def test_wape():
    assert wape(pd.Series([100.0, 100.0]), pd.Series([90.0, 120.0])) == pytest.approx(0.15)


def test_features_pre_christmas():
    f = features(pd.date_range("2011-12-20", "2011-12-31"), "UK")
    assert f["days_to_christmas"].iloc[0] == 5 and f["days_to_christmas"].min() == -6
