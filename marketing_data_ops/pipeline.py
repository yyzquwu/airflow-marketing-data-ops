from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from marketing_data_ops.config import PipelineConfig, load_config
from marketing_data_ops.io import SOURCE_FILES, read_source, write_campaign_daily
from marketing_data_ops.transform import build_unified_campaign_daily
from marketing_data_ops.validation import validate_source


SOURCE_DATE_COLUMNS = {
    "google_ads": "date",
    "meta_ads": "date_start",
    "tiktok_ads": "stat_time_day",
    "youtube_ads": "date",
    "microsoft_ads": "date",
    "other_ads": "date",
}


def project_root_from_file(current_file: str | Path) -> Path:
    return Path(current_file).resolve().parents[1]


def load_raw_sources(project_root: Path) -> dict[str, pd.DataFrame]:
    return {source: read_source(project_root, source) for source in SOURCE_FILES}


def validate_sources(source_frames: dict[str, pd.DataFrame], config: PipelineConfig) -> None:
    reference_date = date.fromisoformat(config.reference_date)
    for source, df in source_frames.items():
        validate_source(
            df=df,
            source=source,
            required_columns=config.required_columns[source],
            metric_columns=config.non_negative_metrics,
            date_column=SOURCE_DATE_COLUMNS[source],
            reference_date=reference_date,
            max_lag_days=config.max_lag_days,
        )


def run_pipeline(project_root: Path) -> Path:
    config = load_config(project_root)
    source_frames = load_raw_sources(project_root)
    validate_sources(source_frames, config)
    unified = build_unified_campaign_daily(source_frames)
    return write_campaign_daily(unified, config.unified_campaign_daily)
