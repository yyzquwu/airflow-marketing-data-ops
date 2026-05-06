from __future__ import annotations

from pathlib import Path

import pandas as pd


SOURCE_FILES = {
    "google_ads": Path("data/raw/google_ads/campaign_daily.csv"),
    "meta_ads": Path("data/raw/meta_ads/campaign_daily.csv"),
    "tiktok_ads": Path("data/raw/tiktok_ads/campaign_daily.csv"),
}


def read_source(project_root: Path, source: str) -> pd.DataFrame:
    if source not in SOURCE_FILES:
        raise ValueError(f"Unsupported source: {source}")
    return pd.read_csv(project_root / SOURCE_FILES[source])


def write_campaign_daily(df: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
