# Sample Paid Media Extracts

These CSVs are small local fixtures modeled after common public paid media export schemas:

- `google_ads/campaign_daily.csv` resembles a Google Ads campaign performance export, including `spend_micros`.
- `meta_ads/campaign_daily.csv` resembles a Meta Ads Insights campaign export, including `date_start` and action-derived purchases.
- `tiktok_ads/campaign_daily.csv` resembles a TikTok Ads daily report, including `stat_time_day` and conversion counts.

The files are intentionally tiny so the pipeline can run locally in tests, a shell script, or Airflow without external services.

For a real-data extension, use the public Facebook ads conversion dataset mirror documented in the workspace shipping guide, then map:

- `Impressions` to `impressions`
- `Clicks` to `clicks`
- `Spent` to `spend`
- `Total_Conversion` to `conversions`
