"""Command line: `python -m fpacopilot.pipeline {data,build,forecast,commentary,powerbi,all}`.

data       download the UCI workbook and convert it to parquet (network, about 2 minutes)
build      clean -> budget -> star schema in data/snapshot/ + data_quality_report.md
forecast   backtest the forecasting methods and write the December landing
commentary variance commentary (cached LLM text, or the deterministic template without a key)
powerbi    export the star schema as CSV for Power BI
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from fpacopilot.config import RAW_PARQUET, SNAPSHOT


def build() -> None:
    from fpacopilot.budget import build_budget
    from fpacopilot.clean import classify
    from fpacopilot.quality import report
    from fpacopilot.warehouse import build as build_tables
    from fpacopilot.warehouse import save

    lines, counts = classify(pd.read_parquet(RAW_PARQUET))
    tables = build_tables(lines, build_budget(lines))
    save(tables)
    (SNAPSHOT / "cleaning_counts.json").write_text(json.dumps(counts, indent=2))
    report(tables, counts)
    print({k: len(v) for k, v in tables.items()})


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "all"
    if cmd in ("data",):
        from fpacopilot.ingest import download, to_parquet

        download()
        to_parquet()
    if cmd in ("build", "all"):
        build()
    if cmd in ("forecast", "all"):
        from fpacopilot.forecast import run

        run()
    if cmd in ("commentary", "all"):
        from fpacopilot.commentary import run as run_commentary

        run_commentary()
    if cmd in ("powerbi", "all"):
        from fpacopilot.powerbi import export

        export()


if __name__ == "__main__":
    main(sys.argv[1:])
