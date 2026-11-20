# FP&A Forecasting Copilot

[![CI](https://github.com/dmp009/fpa-forecasting-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/dmp009/fpa-forecasting-copilot/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

**Live demo:** [fpa-forecasting-copilot.streamlit.app](https://fpa-forecasting-copilot.streamlit.app/) (Streamlit Community Cloud)

A month-end close for a UK online retailer, built on its real sales: budget vs actual, a
price / volume / mix bridge that explains the gap to the penny, a backtested forecast that gives
the full-year landing, and a variance commentary in which every figure is checked against the
numbers. Runs without an API key; the same star schema feeds a Streamlit app and a Power BI model.

## The business problem

At each month-end an FP&A team has a few days to tell the finance director how revenue compares
with budget, why, and where the year will land. The bridge is rebuilt by hand in Excel and the
commentary is rewritten from scratch every month.

| Persona | Question | What the tool gives |
|---|---|---|
| **FP&A analyst** | Can the pack be ready the day the data lands? | P&L by region and category, the PVM bridge and a draft commentary, all reconciled |
| **Finance director / CFO** | Why are we off budget, and where will the year land? | One page: variance, drivers, landing, recommended action |
| **Commercial / category manager** | Which segment drives the gap? | Variance by region and category, split into volume, mix and price |

Requirements, user stories, KPI definitions and backlog: [docs/business_requirements.md](docs/business_requirements.md).

## What the November 2011 close says

| | GBP |
|---|---:|
| Budget, net revenue Jan-Nov 2011 | £9.47m |
| Volume (fewer units than planned) | -£1.11m |
| Mix (richer region x category mix) | +£250k |
| Price (higher price per unit) | +£167k |
| Returns | -£39k |
| Shipping income | +£59k |
| **Actual, net revenue Jan-Nov 2011** | **£8.80m (-7.1%)** |

- **The gap is a volume problem.** Customers paid a little more per unit and bought a richer mix,
  but bought fewer units than planned, mostly in the UK (-£670k) and Europe (-£127k); Rest of world
  beat budget (+£122k on a small base).
- **Full-year landing: £9.59m against a budget of £10.15m (-5.6%)**, with December forecast at
  £788k (budget £677k). The first nine days of December came in at £463k against £416k expected.
- **The simplest forecast wins.** On a month-by-month backtest (Jan-Nov 2011), last year's same
  month has a WAPE of 9.3%, an FP&A run-rate 11.2% and a gradient-boosting model 28.1%. With two
  years of history the model has seen one December; it is kept as a challenger, not used.

## The solution

```
UCI Online Retail II (1.07m invoice lines, 2009-12 to 2011-12)
  -> cleaning rules + pandera checks -> star schema (DuckDB, parquet)  -> data_quality_report.md
  -> driver-based FY2011 budget (from FY2010 actuals + config/budget.yaml)
  -> P&L and price / volume / mix bridge
  -> forecast backtest (3 methods) -> December forecast -> full-year landing
  -> facts -> commentary (Claude, or a template) -> number check
  -> Streamlit app   |   Power BI CSVs + DAX measures
```

| Piece | Where | Detail |
|---|---|---|
| Cleaning and star schema | `fpacopilot/clean.py`, `warehouse.py`, `quality.py` | Duplicates, cancellations, postage, fees and stock adjustments handled by explicit rules; 3 dimensions, 3 facts |
| Budget | `fpacopilot/budget.py` | Units = FY2010 x (1 + regional growth), price = FY2010 + 3%, returns and shipping at FY2010 ratios |
| Bridge | `fpacopilot/variance.py` | Volume + mix + price + returns + shipping = variance, exactly (tested) |
| Forecast | `fpacopilot/forecast.py` | Seasonal naive, run-rate, gradient boosting; backtest without look-ahead; WAPE by region |
| Commentary | `fpacopilot/commentary.py` | Claude drafts from the facts only; any figure not in the facts rejects the draft; template without a key |
| Power BI | `powerbi/` | CSV export, relationships, [measures.dax](powerbi/measures.dax) with the bridge in DAX |
| App | `app/` | Variance, Forecast & landing, Commentary, Data quality, About |

Method in business language: [docs/methodology.md](docs/methodology.md). Tables and columns:
[docs/data_dictionary.md](docs/data_dictionary.md). Model: [docs/data_model.md](docs/data_model.md).

### The AI part, and why it can be trusted

The language model never computes a number. The pipeline writes a facts file with every figure
already rounded (`£8.80m`, `-7.1%`); Claude (`claude-opus-5-5`) turns it into five paragraphs of
commentary; a checker extracts every amount and percentage from the draft and rejects it if one
does not appear in the facts. Drafts are cached by a hash of the facts, so the app and CI never
call the API, and without a key a deterministic template writes the same five paragraphs.

## Run it

```bash
make install          # Python 3.11+
make test             # 21 tests, uses the committed snapshot
make app              # Streamlit on http://localhost:8501
```

Rebuild from the source data (downloads 45 MB from UCI):

```bash
make data && make all
ANTHROPIC_API_KEY=... make commentary   # optional: LLM draft, checked and cached in data/ai_cache/
```

## Tech

Python, pandas, DuckDB, pandera, scikit-learn, Anthropic SDK, Streamlit, Plotly, Power BI (DAX),
pytest, ruff, GitHub Actions.

## Limits

One retailer and two years of data; the budget is constructed from stated assumptions (no company
publishes its own); product categories come from keywords (92% of sales classified); the data has
no costs, so there is no margin analysis; the DAX has not been run in Power BI Desktop in this
repository. Educational project.

Data: Chen, D. (2012). *Online Retail II*. UCI Machine Learning Repository,
https://doi.org/10.24432/C5CG6D, CC BY 4.0.

## Résumé en français

Ce projet reproduit la clôture mensuelle d'une équipe FP&A sur les ventes réelles d'un
e-commerçant britannique (jeu de données UCI Online Retail II, 2009-2011). Il compare le réel au
budget, explique l'écart par un pont prix / volume / mix qui se réconcilie au centime près, prévoit
décembre pour obtenir l'atterrissage annuel et rédige un commentaire de gestion dont chaque chiffre
est vérifié. À fin novembre 2011, le chiffre d'affaires net est de 8,80 M£ contre un budget de
9,47 M£ (-7,1 %) : l'écart vient des volumes, en partie compensés par le mix et les prix.
L'atterrissage est de 9,59 M£ pour un budget annuel de 10,15 M£. Sur un backtest mois par mois, la
méthode naïve saisonnière (WAPE 9,3 %) bat le modèle de gradient boosting (28,1 %) : avec deux ans
d'historique, le modèle n'a vu qu'un seul mois de décembre. Le commentaire est rédigé par Claude à
partir des seuls faits calculés, ou par un modèle de texte sans clé d'API. Le même schéma en étoile
alimente une application Streamlit et un modèle Power BI (CSV et mesures DAX). Projet pédagogique.
