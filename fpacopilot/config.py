"""Paths and YAML config. Every path is relative to the repo root."""
from __future__ import annotations

from functools import cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW_ZIP = ROOT / "data/raw/online_retail_ii.zip"
RAW_PARQUET = ROOT / "data/raw/online_retail_ii.parquet"
SNAPSHOT = ROOT / "data/snapshot"
AI_CACHE = ROOT / "data/ai_cache"
POWERBI = ROOT / "powerbi"


@cache
def load(name: str) -> dict:
    return yaml.safe_load((ROOT / "config" / f"{name}.yaml").read_text(encoding="utf-8"))


def settings() -> dict:
    return load("settings")


def budget_drivers() -> dict:
    return load("budget")


def categories() -> dict:
    return load("categories")
