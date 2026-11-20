"""Download the UCI Online Retail II workbook and convert it to parquet (`make data`).

The 45 MB workbook is not committed. The cleaned star schema in data/snapshot/ is, so the app,
the tests and CI never need the network.
"""
from __future__ import annotations

import hashlib
import zipfile

import pandas as pd
import requests

from fpacopilot.config import RAW_PARQUET, RAW_ZIP, settings


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download() -> None:
    src = settings()["source"]
    if not RAW_ZIP.exists():
        RAW_ZIP.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(src["url"], timeout=300)
        r.raise_for_status()
        RAW_ZIP.write_bytes(r.content)
    digest = sha256(RAW_ZIP)
    if src.get("sha256") and src["sha256"] != digest:
        raise ValueError(f"{RAW_ZIP.name}: sha256 {digest} does not match config/settings.yaml")
    print(f"{RAW_ZIP.name}: sha256 {digest}")


def to_parquet() -> pd.DataFrame:
    """Both sheets (Dec 2009-Dec 2010 and Dec 2010-Dec 2011) stacked, codes kept as text."""
    text = {"Invoice": str, "StockCode": str, "Description": str, "Country": str}
    with zipfile.ZipFile(RAW_ZIP) as z, z.open("online_retail_II.xlsx") as f:
        sheets = pd.read_excel(f, sheet_name=None, dtype=text)
    df = pd.concat(sheets.values(), ignore_index=True)
    df.to_parquet(RAW_PARQUET)
    return df


if __name__ == "__main__":
    download()
    print(to_parquet().shape)
