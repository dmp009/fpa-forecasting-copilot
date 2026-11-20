PYTHON ?= python3.13
PY ?= .venv/bin/python

.PHONY: install test lint data build forecast commentary powerbi all app

install:
	$(PYTHON) -m venv .venv
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

data:        ## download the UCI workbook (45 MB) and convert it to parquet
	$(PY) -m fpacopilot.pipeline data

build:       ## clean -> budget -> star schema + data_quality_report.md
	$(PY) -m fpacopilot.pipeline build

forecast:
	$(PY) -m fpacopilot.pipeline forecast

commentary:  ## uses Claude when ANTHROPIC_API_KEY is set, else the template
	$(PY) -m fpacopilot.pipeline commentary

powerbi:
	$(PY) -m fpacopilot.pipeline powerbi

all: build forecast commentary powerbi

app:
	$(PY) -m streamlit run app/Home.py
