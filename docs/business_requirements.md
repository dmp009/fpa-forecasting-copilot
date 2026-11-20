# Business requirements

## Context

At every month-end close an FP&A team has a few working days to tell the finance director three
things: how revenue compares with budget, why, and where the year will land. The numbers come from
the sales ledger; the explanation is usually rebuilt by hand in Excel (a price / volume / mix
bridge), and the commentary is written from scratch each month.

This project automates that close for a UK online retailer of gifts and homeware (real
transactions, UCI Online Retail II, December 2009 to December 2011, GBP). The simulated calendar is
the November 2011 close: January to November 2011 are actuals, December is forecast, and the FY2011
budget was set from FY2010 actuals.

## Personas

| Persona | Job | What they need |
|---|---|---|
| **FP&A analyst** | Produces the monthly pack | The bridge, the P&L by region and category and a first draft of the commentary, ready when the data lands, with numbers that tie out |
| **Finance director / CFO** | Explains the month to the CEO and the board | One page: the variance, the drivers, the full-year landing and an action |
| **Commercial / category manager** | Owns a region or a product range | Which segment drives the gap, split into volume, mix and price |

## User stories and acceptance criteria

| ID | Story | Acceptance criteria |
|---|---|---|
| US1 | As an FP&A analyst, I see budget vs actual by month, region and category | Revenue P&L (product sales, returns, net product sales, shipping, net revenue) with actual, budget, variance and variance % ; filter by region |
| US2 | As an FP&A analyst, I explain the variance with a price / volume / mix bridge | Bridge from budget to actual net revenue; volume + mix + price + returns + shipping equals the variance exactly (tested) |
| US3 | As a finance director, I know where the year will land | Full-year landing = Jan-Nov actual + December forecast, compared with the full-year budget |
| US4 | As a finance director, I can trust the forecast method | Three methods backtested month by month on Jan-Nov 2011 using only data available at each month-end; WAPE published per region; the best one is used |
| US5 | As an FP&A analyst, I get a first draft of the commentary | Five paragraphs (headline, drivers, regions, categories, landing). Works without an API key (template); an LLM draft is used only if every figure in it appears in the facts |
| US6 | As a Power BI developer, I can rebuild the report in Power BI | Star-schema CSVs, relationships and DAX measures documented in `powerbi/` |
| US7 | As any user, I can judge the data | Cleaning steps and checks in `data_quality_report.md` and the Data quality page; the build fails if a check fails |

## KPI definitions

| KPI | Definition |
|---|---|
| Net revenue | Product sales + returns (negative) + shipping income. Fees, bank charges and manual adjustments are excluded |
| Variance | Actual - budget (positive = favourable for revenue) |
| Variance % | Variance / budget |
| Volume effect | (Actual units - budget units) x average budget price |
| Mix effect | Sum over region x category segments of actual units x (actual share - budget share) x segment budget price |
| Price effect | Sum over segments of actual units x (actual price - budget price) |
| Return rate | - Returns / product sales |
| Full-year landing | Year-to-date actual + forecast for the remaining month(s) |
| WAPE | Sum of absolute forecast errors / sum of actuals, over the backtest months |

## Project KPIs (targets for the tool itself)

| KPI | Target | Result |
|---|---|---|
| Bridge reconciliation error | 0 (to the penny) | 0, `tests/test_snapshot.py` |
| Data-quality checks failing | 0 | 0, `data_quality_report.md` |
| Commentary figures not in the facts | 0 | 0, enforced by `commentary.check` |
| Forecast WAPE of the chosen method, total | below 15% | 9.3% (seasonal naive) |

## Backlog

| Priority | Item | Status |
|---|---|---|
| Must | Cleaning rules, star schema, data-quality report | Done |
| Must | Driver-based budget, P&L, PVM bridge | Done |
| Must | Forecast backtest and landing | Done |
| Must | Commentary with number check, template fallback | Done |
| Must | Streamlit app, Power BI export and DAX | Done |
| Should | Generate and commit an LLM commentary draft (needs an API key) | Open |
| Should | Open the DAX file in Power BI Desktop and publish screenshots | Open |
| Could | Rolling forecast for more than one month ahead (Q1 2012 outlook) | Open |
| Could | Customer-level drivers (new vs returning customers, order value) in the bridge | Open |
| Won't | Cost of sales and margin (the dataset has revenue only) | Out of scope |

## Out of scope

Costs and margins, cash flow, balance sheet, other companies, a real company budget.
