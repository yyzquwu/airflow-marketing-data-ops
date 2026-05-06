from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from marketing_data_ops.config import load_config
from marketing_data_ops.pipeline import run_pipeline
from marketing_data_ops.reporting import write_incident_report


def main() -> int:
    config = load_config(PROJECT_ROOT)
    try:
        output_path = run_pipeline(PROJECT_ROOT)
    except Exception as error:
        report_path = write_incident_report(
            incidents_dir=config.incidents_dir,
            dag_id="local_marketing_campaign_daily",
            task_id="run_pipeline",
            error=error,
        )
        print(f"Pipeline failed. Incident report written to {report_path}")
        return 1

    print(f"Pipeline succeeded. Unified table written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
