# Data dictionary

Source: Chen, D. (2012). *Online Retail II*. UCI Machine Learning Repository,
https://doi.org/10.24432/C5CG6D, CC BY 4.0. Two Excel sheets (2009-2010 and 2010-2011), 1,067,371
invoice lines, one UK online retailer of gifts and homeware (many customers are wholesalers).

## Raw columns

| Column | Meaning |
|---|---|
| Invoice | Invoice number; a leading "C" marks a cancellation |
| StockCode | Product code (5 digits + optional letter); other codes are postage, fees or adjustments |
| Description | Product name |
| Quantity | Units per line (negative on cancellations) |
| InvoiceDate | Date and time |
| Price | Unit price, GBP |
| Customer ID | Customer number (missing on about a fifth of lines) |
| Country | Customer country |

## Star schema (`data/snapshot/*.parquet`, `powerbi/data/*.csv`)

### dim_date (one row per day)
| Column | Type | Meaning |
|---|---|---|
| date | date | Key |
| year, quarter, month | int | Calendar parts |
| month_start | date | First day of the month (joins the month-grain budget) |
| month_name | text | Jan..Dec |
| iso_week, weekday | int | ISO week; 0 = Monday |
| is_weekend | bool | Saturday or Sunday |

### dim_product (one row per stock code)
| Column | Type | Meaning |
|---|---|---|
| stock_code | text | Key |
| description | text | Latest description |
| category | text | Keyword category (`config/categories.yaml`), "Non-product" for postage and fees |

### dim_market (one row per country)
| Column | Type | Meaning |
|---|---|---|
| country | text | Key |
| region | text | UK, Europe or Rest of world (`config/settings.yaml`) |

### fact_sales (day x stock code x country x P&L line)
| Column | Type | Meaning |
|---|---|---|
| date, stock_code, country | keys | Foreign keys to the dimensions |
| line_type | text | product, return, shipping, other |
| units | int | Sum of quantity |
| revenue | float | Sum of quantity x price, GBP (returns negative) |
| lines | int | Number of invoice lines aggregated |

### fact_invoices (one row per invoice, product and return lines only)
| Column | Type | Meaning |
|---|---|---|
| invoice | text | Key |
| date, country, customer_id | | Invoice attributes |
| cancelled | bool | Invoice starts with "C" |
| units, revenue | | Totals of the invoice |

### fact_budget (month x region x category x P&L line, FY2011)
| Column | Type | Meaning |
|---|---|---|
| month_start | date | Month |
| region, category | text | Segment ("Non-product" for returns and shipping) |
| line_type | text | product, return, shipping |
| units | float | Budget units (0 for returns and shipping) |
| price | float | Budget average price |
| revenue | float | Budget revenue, GBP |

### Outputs
| File | Content |
|---|---|
| forecast_backtest.parquet | region, month, one forecast per method, actual |
| forecast_december.parquet | December 2011 forecast per region and method |
| forecast_summary.json | WAPE per method and region; landing figures |
| commentary_facts.json | The formatted figures the commentary may use |
| data/ai_cache/commentary.json | Cached LLM draft (present only when generated with a key) |

## Lineage

```
UCI zip (data/raw, git-ignored) -> online_retail_ii.parquet -> clean.classify
  -> budget.build_budget (FY2010 lines + config/budget.yaml)
  -> warehouse.build -> data/snapshot/*.parquet (committed) -> DuckDB views (v_sales)
     -> variance (P&L, bridge) -> forecast (backtest, landing) -> commentary (facts, text, check)
     -> powerbi/data/*.csv -> Power BI model + powerbi/measures.dax
```
