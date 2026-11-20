# Power BI: build the report from the star schema

The repository ships the model as CSV + DAX rather than a `.pbix` (a binary file that cannot be
reviewed in a pull request). Building it takes about fifteen minutes in Power BI Desktop.

## 1. Export the tables

```bash
make powerbi        # writes powerbi/data/*.csv from data/snapshot (no download needed)
```

| File | Rows |
|---|---:|
| dim_date.csv | 739 |
| dim_product.csv | 4,954 |
| dim_market.csv | 43 |
| dim_category.csv | 10 |
| dim_region.csv | 3 |
| fact_sales.csv | 601,651 |
| fact_invoices.csv | 46,921 |
| fact_budget.csv | 391 |

## 2. Load

Get data > Text/CSV, load all eight files. In Power Query set `date` and `month_start` to Date,
`revenue`, `units` and `price` to Decimal number, `cancelled` and `is_weekend` to True/False.
Mark `dim_date` as the date table (Table tools > Mark as date table > `date`).

## 3. Relationships (Model view)

| From (many) | To (one) | Note |
|---|---|---|
| fact_sales[date] | dim_date[date] | |
| fact_sales[stock_code] | dim_product[stock_code] | |
| fact_sales[country] | dim_market[country] | |
| fact_invoices[date] | dim_date[date] | |
| fact_invoices[country] | dim_market[country] | |
| fact_budget[month_start] | dim_date[date] | the budget sits on the first day of each month |
| fact_budget[region] | dim_region[region] | |
| fact_budget[category] | dim_category[category] | |
| dim_market[region] | dim_region[region] | so a region filter reaches the actuals |
| dim_product[category] | dim_category[category] | so a category filter reaches the actuals |

All single-direction, one-to-many. Slice by `dim_region`, `dim_category` and `dim_date`, never by
`dim_market[region]` or `dim_product[category]` (those do not reach the budget).

## 4. Measures

Create an empty table `_Measures` (Enter data, one blank column, then delete it) and paste the
measures from [measures.dax](measures.dax). They mirror `fpacopilot/variance.py`: Net Revenue,
Budget Net Revenue, Variance, Variance %, YTD versions at the 30 November 2011 close, and the
Volume / Mix / Price / Returns / Shipping effects of the bridge.

## 5. Suggested pages

1. **Overview**: cards for Net Revenue YTD, Budget Net Revenue YTD, Variance YTD, Variance %;
   clustered column of Net Revenue vs Budget Net Revenue by `dim_date[month_start]`.
2. **Bridge**: waterfall chart with the five effect measures (Format > Breakdown, or a small
   disconnected table of step names with a SWITCH measure).
3. **Regions & categories**: matrix `dim_region` x `dim_category` with Variance and Variance %,
   conditional formatting red / green.

Check: at total level, Volume + Mix + Price + Returns + Shipping effects equal Variance, and
Variance YTD equals -£675k (the same figure as the Streamlit app and `tests/test_snapshot.py`).

The DAX has been written against this model but not run in Power BI Desktop inside this repository
(it is developed on macOS); please open an issue if a measure needs a fix.
