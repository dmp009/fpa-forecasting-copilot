# Methodology

## 1. Cleaning (`fpacopilot/clean.py`)

| Rule | Why |
|---|---|
| Drop exact duplicate lines (34,335) | The same line scanned twice would double revenue |
| A product is a stock code of five digits with an optional letter suffix | Other codes are postage, fees, bank charges, manual adjustments and tests |
| POST, DOT and C2 are shipping income | Postage charged to customers is revenue, reported on its own line |
| Other non-product codes are "other" and excluded from net revenue | Amazon fees, bank charges, bad-debt write-offs are not sales |
| Product lines with price 0 or below are dropped (5,928) | Stock adjustments, not sales |
| Product lines on a "C" invoice are returns | Cancellations reduce revenue |
| One description per stock code (the most frequent) gives the category | A product never sits in two categories |

Categories come from ordered keyword lists in `config/categories.yaml` (for example "CHRISTMAS"
before "CANDLE"); 92% of product sales are classified, the rest is "Accessories & other".

## 2. Budget (`fpacopilot/budget.py`, `config/budget.yaml`)

No company publishes its internal budget, so it is built the way a planner would in late 2010,
from FY2010 actuals only:

- **units** = FY2010 units of the same month x (1 + regional growth + category override).
  Growth: UK +5%, Europe +12%, Rest of world +8%; Christmas & seasonal +3 points, Toys & kids -2.
- **price** = FY2010 average price of the region x category, +3% list-price increase.
- **returns** and **shipping** = FY2010 ratio to product sales, by region.

Grain: month x region x category (product sales) and month x region (returns, shipping).

## 3. Price / volume / mix bridge (`fpacopilot/variance.py`)

For product sales, with segments i = region x category, units u, price p = revenue / u,
total units U, unit shares w = u / U and the average budget price P = budget revenue / U_bud:

```
volume = (U_act - U_bud) x P_bud
mix    = sum_i  U_act x (w_act,i - w_bud,i) x p_bud,i
price  = sum_i  u_act,i x (p_act,i - p_bud,i)
```

volume + mix + price = actual - budget product sales, exactly. A segment with no budget is valued
at its actual price, so all of its revenue is mix (a new segment is a mix effect, not a price
effect). Returns and shipping are added as their own steps, so the bridge ends at net revenue.

YTD (Jan-Nov 2011): budget £9.47m; volume -£1.11m, mix +£250k, price +£167k, returns -£39k,
shipping +£59k; actual £8.80m (-7.1%). Fewer units than planned is the whole story: customers
paid slightly more per unit and bought a richer mix, but not enough to make up for volume.

## 4. Forecast and landing (`fpacopilot/forecast.py`)

Monthly net revenue per region is forecast from the close of the previous month, never using data
from the month itself:

| Method | How |
|---|---|
| Seasonal naive | Same month last year |
| Run-rate (FP&A) | Same month last year x year-on-year growth of the last three closed months |
| Gradient boosting | scikit-learn `HistGradientBoostingRegressor` on daily revenue scaled by the region's level over the 28 days before the forecast origin; features: region, weekday, day, month, days to Christmas; daily forecasts summed to the month |

Backtest: each month from January to November 2011. WAPE (total absolute error / total actual):

| Region | Seasonal naive | Run-rate | Gradient boosting |
|---|---:|---:|---:|
| Total | 9.3% | 11.2% | 28.1% |
| UK | 9.0% | 10.1% | 27.1% |
| Europe | 18.6% | 16.8% | 37.6% |
| Rest of world | 71.5% | 112.3% | 112.8% |

**In business terms:** the simplest method wins. With two years of data the model has seen one
December, one Black-Friday ramp and one year of a business that grew unevenly by region: not
enough history to learn a better pattern than "same month last year". The gradient-boosting model
stays as a challenger and is re-tested every month; the run-rate adds value only where growth is
stable (Europe). Rest of world is small and lumpy (a few large wholesale orders), so every method
is poor there and the forecast should be read at total level.

Landing: December forecast £788k (seasonal naive) against a December budget of £677k; full year
£9.59m against £10.15m (-5.6%). A partial check: the data stops on 9 December 2011, and actual
revenue to that date was £463k against £416k expected from the forecast spread by last
December's daily pattern.

## 5. Commentary (`fpacopilot/commentary.py`)

1. `facts()` computes every figure the commentary may use, already rounded and formatted.
2. The text is written by Claude (`claude-opus-5-5`, effort medium, with server-side refusal
   fallbacks enabled) from those facts only, when `ANTHROPIC_API_KEY` is set; otherwise a
   deterministic template writes it. LLM drafts are cached in `data/ai_cache/` keyed by a hash of
   the facts, so the app and CI never call the API.
3. `check()` extracts every figure (amounts, percentages) from the text and rejects the draft if
   one does not appear in the facts. Years and small counts are allowed. A rejected draft is
   never shown; the template is used instead.

## 6. Limits

One retailer and two years; the budget is constructed; keyword categories are approximate; the
data has no costs, so there is no margin analysis; the DAX measures mirror the Python logic but
have not been run in Power BI Desktop in this repository.
