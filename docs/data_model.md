# Data model

```
                 dim_date (date, month_start, ...)
                   |  1:* date              \  1:* date = fact_budget[month_start]
                   v                         v (budget sits on the first day of each month)
dim_product --1:*-- fact_sales --*:1-- dim_market --*:1-- dim_region
 (stock_code,        (date, stock_code,   (country,           (region)
  category)           country, line_type)  region)               |
     |                                                           | 1:*
     *:1                                                         v
dim_category --------------------1:*--------------------- fact_budget
 (category)                                         (month_start, region, category, line_type)

fact_invoices --*:1-- dim_date, dim_market (invoice-level orders and customers)
```

- **Actuals** are at day x product x country grain; the **budget** is at month x region x category
  grain, dated on the first day of the month, so it joins dim_date[date] directly and any month,
  quarter or year filter applies to both. They meet at the shared dimensions month, region and category, which is how a budget is
  usually compared with actuals in a BI model.
- In DuckDB the view `v_sales` joins fact_sales to dim_date, dim_product and dim_market.
- In Power BI, dim_category and dim_region (exported only for Power BI) carry the budget
  relationships; dim_product -> dim_category and dim_market -> dim_region make actuals and budget
  filter together. Relationship list: `powerbi/README.md`.
