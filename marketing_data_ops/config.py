from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PipelineConfig:
    max_lag_days: int
    reference_date: str
    required_columns: dict[str, list[str]]
    non_negative_metrics: list[str]
    unified_campaign_daily: Path
    incidents_dir: Path


def load_config(project_root: Path, config_path: Path | None = None) -> PipelineConfig:
    path = config_path or project_root / "config" / "pipeline.yml"
    with path.open("r", encoding="utf-8") as file:
        raw: dict[str, Any] = yaml.safe_load(file)

    return PipelineConfig(
        max_lag_days=int(raw["freshness"]["max_lag_days"]),
        reference_date=str(raw["freshness"]["reference_date"]),
        required_columns=raw["quality"]["required_columns"],
        non_negative_metrics=list(raw["quality"]["non_negative_metrics"]),
        unified_campaign_daily=project_root / raw["output"]["unified_campaign_daily"],
        incidents_dir=project_root / raw["output"]["incidents_dir"],
    )

