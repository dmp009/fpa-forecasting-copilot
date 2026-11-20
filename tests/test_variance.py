import pandas as pd
import pytest

from fpacopilot import variance as v


def frame(rows):
    return pd.DataFrame(rows, columns=["month_start", "region", "category", "line_type", "units", "revenue"])


M = pd.Timestamp("2011-01-01")
BUD = frame([
    (M, "UK", "A", "product", 100, 1000.0), (M, "UK", "B", "product", 50, 250.0),
    (M, "UK", "Non-product", "return", 0, -40.0), (M, "UK", "Non-product", "shipping", 0, 30.0),
])
ACT = frame([
    (M, "UK", "A", "product", 80, 880.0), (M, "UK", "B", "product", 90, 405.0), (M, "UK", "C", "product", 10, 70.0),
    (M, "UK", "Non-product", "return", 0, -60.0), (M, "UK", "Non-product", "shipping", 0, 35.0),
])


def test_bridge_reconciles_exactly():
    br = v.bridge(ACT, BUD)
    assert br.budget_net == pytest.approx(1240.0)
    assert br.actual_net == pytest.approx(1330.0)
    steps = br.volume + br.mix + br.price + br.returns + br.shipping
    assert br.budget_net + steps == pytest.approx(br.actual_net)
    assert br.returns == pytest.approx(-20.0) and br.shipping == pytest.approx(5.0)


def test_pvm_segments_sum_to_product_variance():
    seg = v.pvm(ACT, BUD)
    assert (seg["volume"] + seg["mix"] + seg["price"]).sum() == pytest.approx(seg["variance"].sum())
    assert seg["variance"].sum() == pytest.approx(1355.0 - 1250.0)


def test_volume_and_price_by_hand():
    seg = v.pvm(ACT, BUD).set_index("category")
    # total units 180 vs 150 at the average budget price 1250/150
    assert seg["volume"].sum() == pytest.approx(30 * 1250 / 150)
    # A: 80 units x (11 - 10); B: 90 x (4.5 - 5)
    assert seg.loc["A", "price"] == pytest.approx(80.0)
    assert seg.loc["B", "price"] == pytest.approx(-45.0)


def test_unbudgeted_segment_lands_in_mix():
    seg = v.pvm(ACT, BUD).set_index("category")
    assert seg.loc["C", "price"] == pytest.approx(0.0)
    assert seg.loc["C", "volume"] == pytest.approx(0.0)
    assert seg.loc["C", "mix"] == pytest.approx(70.0)


def test_pnl_lines():
    p = v.pnl(ACT, BUD)
    assert p[("actual", "net_revenue")].iloc[0] == pytest.approx(1330.0)
    assert p[("variance", "net_product")].iloc[0] == pytest.approx(1295.0 - 1210.0)
