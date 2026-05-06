from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import traceback


def write_incident_report(
    incidents_dir: Path,
    dag_id: str,
    task_id: str,
    error: BaseException,
    run_id: str | None = None,
) -> Path:
    incidents_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_run_id = (run_id or "manual").replace("/", "_").replace(":", "_")
    report_path = incidents_dir / f"{timestamp}_{dag_id}_{task_id}_{safe_run_id}.md"

    report_path.write_text(
        "\n".join(
            [
                f"# Incident Report: {dag_id}.{task_id}",
                "",
                f"- Status: failed",
                f"- Detected at UTC: {timestamp}",
                f"- Run ID: {run_id or 'manual'}",
                f"- Error type: {type(error).__name__}",
                f"- Error message: {error}",
                "",
                "## Immediate Triage",
                "",
                "1. Confirm the source CSV landed in `data/raw/<source>/`.",
                "2. Check required columns and metric values against `config/pipeline.yml`.",
                "3. Rerun the DAG after correcting the extract or freshness window.",
                "",
                "## Traceback",
                "",
                "```text",
                "".join(traceback.format_exception(type(error), error, error.__traceback__)).strip(),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report_path

