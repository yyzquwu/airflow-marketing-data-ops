# Airflow Marketing Data Ops

I built this as a small but realistic marketing data ops project: an Airflow-style pipeline, a normalized paid media table, and a Streamlit dashboard that uses the same real Kaggle Global Ads Performance dataset as my React dashboard.

The main idea is simple: take campaign data from paid media platforms, clean it into one analytics-ready table, and make the dashboard easy to use for quick performance checks.

## What Is Inside

- Airflow DAG for a daily marketing campaign workflow
- Reusable Python pipeline code for validation and normalization
- Streamlit dashboard for campaign performance analysis
- Real Kaggle-backed dashboard data for Google Ads, Meta, and TikTok
- Local portfolio sample data for the Airflow pipeline demo
- Tests for the pipeline and dashboard data loading

## Dashboard

The Streamlit dashboard defaults to:

```text
data/public/global_ads_performance_daily.csv
```

That file is normalized from:

```text
data/public/raw_global_ads_performance_dataset.csv
```

It matches the Kaggle dataset used in my React dashboard branch, so the headline stats line up across both apps:

- Total spend
- Conversions
- CPA
- CTR
- CPC
- Revenue
- ROAS

The dashboard also includes filters for date range, platform, campaign, source/medium, country, and industry.

## Project Layout

```text
airflow-marketing-data-ops/
  dags/                         Airflow DAG
  marketing_data_ops/           Pipeline package
  data/raw/                     Portfolio sample extracts
  data/public/                  Kaggle dashboard dataset
  dashboard/app.py              Streamlit dashboard
  config/pipeline.yml           Validation and freshness rules
  scripts/                      Local pipeline helpers
  tests/                        Pipeline and dashboard tests
  docker-compose.yml            Local Airflow option
```

## Run It Locally

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the local pipeline sample:

```bash
python scripts/run_pipeline.py
```

Open the dashboard:

```bash
streamlit run dashboard/app.py
```

Run tests:

```bash
pytest
```

## Airflow Demo

To run the Airflow version locally:

```bash
docker compose up
```

Then open `http://localhost:8080` and trigger the `marketing_campaign_daily` DAG.

The DAG reads sample extracts from `data/raw/`, validates them, and writes the unified output to:

```text
output/unified_campaign_daily.csv
```

## Data Model

The dashboard and pipeline use a daily campaign grain.

| Column | Meaning |
| --- | --- |
| `date` | Campaign performance date |
| `source` / `source_label` | Platform, like Google Ads, Meta, or TikTok |
| `campaign_id` / `campaign_name` | Campaign identifiers |
| `segment` | Country or reporting segment |
| `impressions`, `clicks`, `spend`, `conversions`, `revenue` | Core performance metrics |
| `ctr`, `cpc`, `cpa`, `roas` | Derived performance metrics |

## Why I Made This

I wanted this repo to feel like the kind of marketing analytics work I would actually hand to a team: clear data contracts, simple validation, useful failure notes, and a dashboard that tells the same story as the underlying dataset.

It is intentionally compact, but the pieces are separated the way I would separate them in a real workflow: orchestration, transformation, validation, dashboarding, and documentation.
