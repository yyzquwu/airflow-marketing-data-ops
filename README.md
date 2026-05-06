# Airflow Marketing Data Ops

A GitHub-ready Airflow demo for a marketing data operations workflow:

1. Ingest raw paid media CSV extracts.
2. Validate schema, non-negative metrics, and freshness.
3. Transform Google Ads, Meta Ads, and TikTok Ads extracts into a unified daily campaign table.
4. Write a Markdown incident report when a task fails.

The project uses only local files and small documented sample extracts in `data/raw/`.

The sample extracts are modeled after common paid media schemas and public campaign-performance datasets, including Google's public analytics sample and public Kaggle-style ad performance datasets. Real Meta, Google Ads, and TikTok exports normally require account credentials, so this project keeps the operational workflow runnable offline.

The repo also includes `data/public/public_facebook_ads_sample.csv`, a 150-row normalized public Facebook ads conversion sample for reviewers who want to inspect a real campaign dataset alongside the runnable local extracts.

## Project Layout

```text
airflow-marketing-data-ops/
  dags/marketing_campaign_daily.py        # Airflow DAG
  marketing_data_ops/                     # Reusable pipeline package
  data/raw/                               # Sample paid media source extracts
  config/pipeline.yml                     # Freshness, quality, and output settings
  scripts/run_pipeline.py                 # Local runner without Airflow
  tests/test_pipeline.py                  # Unit/integration tests
  docker-compose.yml                      # Lightweight Airflow standalone option
```

## Data Model

The output table is written to `output/unified_campaign_daily.csv`.

| Column | Description |
| --- | --- |
| `date` | Campaign performance date. |
| `source` | Paid media platform, such as `google_ads` or `meta_ads`. |
| `account_id` | Platform account ID. |
| `campaign_id` | Platform campaign ID. |
| `campaign_name` | Human-readable campaign name. |
| `impressions`, `clicks`, `spend`, `conversions` | Daily delivery and conversion metrics. |
| `ctr`, `cpc`, `cpa` | Derived performance metrics. |

Google Ads sample spend is stored as `spend_micros` and normalized to currency units. Meta Ads sample purchases are stored as `actions_purchase` and normalized to `conversions`. TikTok sample dates use `stat_time_day` and are normalized to the same daily reporting grain.

## Quick Start

Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the pipeline locally:

```bash
python scripts/run_pipeline.py
```

Run tests:

```bash
pytest
```

On Windows, run Airflow itself through Docker or WSL2. Apache Airflow is designed for POSIX-style environments, and native Windows DAG execution can hit POSIX-only imports such as `fcntl`.

## Run With Airflow

The fastest demo path is Airflow standalone through Docker Compose:

```bash
docker compose up
```

Open `http://localhost:8080`, find the `marketing_campaign_daily` DAG, and trigger it manually. Airflow standalone prints the generated admin credentials in the container logs.

The DAG reads local files from `data/raw/` and writes the unified table to `output/unified_campaign_daily.csv`.

To run a non-interactive DAG test:

```bash
docker compose run --rm airflow bash -c "airflow db migrate && airflow dags test marketing_campaign_daily 2026-05-05"
```

## Validation Rules

Rules live in `config/pipeline.yml`.

- Required columns are checked per source.
- Extracts must be non-empty.
- Numeric metrics listed under `quality.non_negative_metrics` cannot be negative.
- Latest source partition must be within `freshness.max_lag_days` of `freshness.reference_date`.

For a live deployment, replace `freshness.reference_date` with the Airflow logical date or a runtime parameter. It is pinned here so tests and portfolio demos are deterministic.

## Incident Runbook

On failure, the DAG callback writes a Markdown incident report to `output/incidents/`.

Local runner failures also create an incident report with:

- failing task name,
- error type and message,
- UTC detection timestamp,
- immediate triage checklist,
- traceback for debugging.

Common fixes:

- Missing column: update the extract or `config/pipeline.yml` if the upstream schema intentionally changed.
- Negative metric: inspect upstream platform adjustments, refunds, or malformed input.
- Stale extract: confirm the file landed in `data/raw/<source>/` or adjust the freshness window for backfills.

## Portfolio Notes

This repo is intentionally small but shaped like production data ops work:

- Airflow orchestration is separated from business logic.
- Data quality checks fail early before transformation.
- The transform produces a stable analytics table contract.
- Incident reporting creates an artifact that an analyst or on-call owner can use immediately.
