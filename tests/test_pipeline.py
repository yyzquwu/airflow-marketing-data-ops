from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from marketing_data_ops.config import load_config
from marketing_data_ops.exceptions import DataQualityError
from marketing_data_ops.io import SOURCE_FILES
from marketing_data_ops.pipeline import load_raw_sources, run_pipeline, validate_sources
from marketing_data_ops.transform import build_unified_campaign_daily


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_build_unified_campaign_daily_has_expected_columns() -> None:
    source_frames = load_raw_sources(PROJECT_ROOT)
    unified = build_unified_campaign_daily(source_frames)

    assert list(unified.columns) == [
        "date",
        "source",
        "account_id",
        "campaign_id",
        "campaign_name",
        "impressions",
        "clicks",
        "spend",
        "conversions",
        "ctr",
        "cpc",
        "cpa",
    ]
    assert set(unified["source"]) == set(SOURCE_FILES)
    assert len(unified) == 3007
    assert unified["campaign_name"].nunique() == 97
    assert unified["spend"].sum() == pytest.approx(4_238_741.58)


def test_validate_sources_rejects_negative_metrics() -> None:
    source_frames = load_raw_sources(PROJECT_ROOT)
    source_frames["meta_ads"].loc[0, "spend"] = -10

    with pytest.raises(DataQualityError, match="negative values"):
        validate_sources(source_frames, load_config(PROJECT_ROOT))


def test_run_pipeline_writes_unified_table(tmp_path: Path) -> None:
    project_copy = tmp_path / "project"
    project_copy.mkdir()
    for directory in ["config", *[str(Path("data/raw") / source) for source in SOURCE_FILES]]:
        (project_copy / directory).mkdir(parents=True, exist_ok=True)

    (project_copy / "config/pipeline.yml").write_text(
        (PROJECT_ROOT / "config/pipeline.yml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    for source, relative_path in SOURCE_FILES.items():
        src = PROJECT_ROOT / relative_path
        dst = project_copy / relative_path
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    output_path = run_pipeline(project_copy)
    output = pd.read_csv(output_path)

    assert output_path.exists()
    assert len(output) == 3007
    assert output.loc[output["campaign_id"] == "g-0001", "source"].iloc[0] == "google_ads"
