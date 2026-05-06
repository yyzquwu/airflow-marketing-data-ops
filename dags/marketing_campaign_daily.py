from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from airflow.decorators import dag, task
from airflow.operators.python import get_current_context

from marketing_data_ops.config import load_config
from marketing_data_ops.pipeline import build_unified_campaign_daily, load_raw_sources, validate_sources
from marketing_data_ops.reporting import write_incident_report
from marketing_data_ops.io import write_campaign_daily


PROJECT_ROOT = Path(
    os.environ.get("MARKETING_DATA_OPS_PROJECT_ROOT", Path(__file__).resolve().parents[1])
).resolve()
DAG_ID = "marketing_campaign_daily"


def report_failure(context: dict) -> None:
    exception = context.get("exception") or RuntimeError("Task failed without an exception in context")
    task_instance = context["task_instance"]
    config = load_config(PROJECT_ROOT)
    write_incident_report(
        incidents_dir=config.incidents_dir,
        dag_id=DAG_ID,
        task_id=task_instance.task_id,
        error=exception,
        run_id=context.get("run_id"),
    )


@dag(
    dag_id=DAG_ID,
    start_date=datetime(2026, 5, 1),
    schedule="@daily",
    catchup=False,
    default_args={"on_failure_callback": report_failure},
    tags=["marketing", "paid-media", "data-quality"],
)
def marketing_campaign_daily_dag():
    @task
    def ingest_raw_extracts() -> dict:
        source_frames = load_raw_sources(PROJECT_ROOT)
        return {source: frame.to_json(orient="records") for source, frame in source_frames.items()}

    @task
    def validate_raw_extracts(serialized_frames: dict) -> dict:
        from io import StringIO

        import pandas as pd

        source_frames = {
            source: pd.read_json(StringIO(payload), orient="records")
            for source, payload in serialized_frames.items()
        }
        validate_sources(source_frames, load_config(PROJECT_ROOT))
        return serialized_frames

    @task
    def transform_campaign_daily(serialized_frames: dict) -> str:
        from io import StringIO

        import pandas as pd

        source_frames = {
            source: pd.read_json(StringIO(payload), orient="records")
            for source, payload in serialized_frames.items()
        }
        unified = build_unified_campaign_daily(source_frames)
        config = load_config(PROJECT_ROOT)
        output_path = write_campaign_daily(unified, config.unified_campaign_daily)
        return str(output_path)

    @task(trigger_rule="all_success")
    def log_success(output_path: str) -> None:
        context = get_current_context()
        print(f"Wrote unified campaign table to {output_path} for run {context.get('run_id')}")

    raw = ingest_raw_extracts()
    validated = validate_raw_extracts(raw)
    output = transform_campaign_daily(validated)
    log_success(output)


marketing_campaign_daily_dag()
