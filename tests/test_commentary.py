from fpacopilot.commentary import check, money, pct, template

FACTS = {
    "period": "January to November 2011 (year to date at the 2011-11-30 close)",
    "ytd": {"net_revenue_actual": "£8.80m", "net_revenue_budget": "£9.47m", "variance": "-£675k", "variance_pct": "-7.1%"},
    "bridge": {"volume": "-£1.11m", "mix": "£250k", "price": "£167k", "returns": "-£39k", "shipping": "£59k"},
    "regions": {"UK": {"actual": "£7.35m", "budget": "£8.02m", "variance": "-£670k", "variance_pct": "-8.4%"}},
    "categories": {"largest_shortfall": {"category": "Home decor", "variance": "-£281k", "volume": "-£114k"},
                   "largest_beat": {"category": "Kitchen & dining", "variance": "£188k", "mix": "£315k", "price": "£172k"}},
    "landing": {"method": "Seasonal naive", "december_forecast": "£788k", "december_budget": "£677k",
                "full_year_landing": "£9.59m", "full_year_budget": "£10.15m", "full_year_gap": "-£565k",
                "full_year_gap_pct": "-5.6%"},
}


def test_formats():
    assert money(8_799_507) == "£8.80m" and money(-674_000) == "-£674k"
    assert pct(-0.0712) == "-7.1%" and pct(0.5) == "+50.0%"


def test_template_passes_the_check():
    assert check(template(FACTS), FACTS) == []


def test_check_rejects_invented_or_recomputed_figures():
    assert check("Revenue was £8.80m, down 7.1%.", FACTS) == []
    assert check("Revenue was £8.81m.", FACTS) == ["£8.81m"]
    assert check("The gap is 12.3% of budget.", FACTS) == ["12.3%"]
    assert check("Price added £167k, volume £1,234k.", FACTS) == ["£1,234k"]


def test_check_allows_years_and_small_counts():
    assert check("In 2011 the top 3 categories grew; see the 30 November close.", FACTS) == []
