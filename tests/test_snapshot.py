"""Run over the committed star schema (data/snapshot)."""
import json

import pytest

from fpacopilot import variance as v
from fpacopilot.commentary import check, facts, get
from fpacopilot.config import SNAPSHOT
from fpacopilot.warehouse import connect


@pytest.fixture(scope="module")
def con():
    return connect()


def test_ytd_bridge_reconciles(con):
    act, bud = v.actuals(con, "2011-01-01", "2011-11-30"), v.budget(con, "2011-01-01", "2011-11-30")
    br = v.bridge(act, bud)
    total = br.budget_net + br.volume + br.mix + br.price + br.returns + br.shipping
    assert total == pytest.approx(br.actual_net, abs=0.01)
    assert br.actual_net < br.budget_net  # the year is behind budget


def test_budget_is_twelve_months_three_regions(con):
    row = con.execute("SELECT count(DISTINCT month_start), count(DISTINCT region) FROM fact_budget").fetchone()
    assert row == (12, 3)


def test_landing_adds_up():
    land = json.loads((SNAPSHOT / "forecast_summary.json").read_text())["landing"]
    assert land["full_year_landing"] == pytest.approx(land["ytd_actual"] + land["december_forecast"])


def test_shipped_commentary_passes_the_check():
    f = facts()
    out = get(f)
    assert out["text"] and check(out["text"], f) == []
