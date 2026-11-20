# Data quality report

Source: Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D Licence CC BY 4.0.

## Cleaning

| Step | Rows |
|---|---:|
| raw rows | 1,067,371 |
| duplicates dropped | 34,335 |
| zero price product lines dropped | 5,928 |
| lines product | 1,003,214 |
| lines return | 17,914 |
| lines shipping | 3,788 |
| lines other | 2,192 |
| clean rows | 1,027,108 |

## Checks

| Check | Result | Detail |
|---|---|---|
| Every fact row has a product in dim_product | pass |  |
| Every fact row has a market in dim_market | pass |  |
| Invoice table reconciles to product + return revenue | pass | 18,926,266.18 vs 18,926,266.18 |
| Budget covers 12 months x 3 regions | pass |  |
| Returns are negative revenue | pass |  |
| Keyword categories cover at least 85% of product sales | pass | 92.0% |

Schemas (types, allowed values, unique keys) are validated with pandera before the snapshot is saved.
