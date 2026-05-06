# Sample Paid Media Extracts

These CSVs are local fixtures modeled after common public paid media export schemas:

- `google_ads/campaign_daily.csv` resembles a Google Ads campaign performance export, including `spend_micros`.
- `meta_ads/campaign_daily.csv` resembles a Meta Ads Insights campaign export, including `date_start` and action-derived purchases.
- `tiktok_ads/campaign_daily.csv` resembles a TikTok Ads daily report, including `stat_time_day` and conversion counts.
- `youtube_ads/campaign_daily.csv` resembles a YouTube campaign export with spend stored in micros.
- `microsoft_ads/campaign_daily.csv` resembles a Microsoft Ads campaign export.
- `other_ads/campaign_daily.csv` gives the dashboard an "Other" paid media bucket.

The included sample is portfolio-scale but still lightweight: 3,007 raw rows covering 97 campaigns, 31 days, and 6 paid media sources. It is generated deterministically by `scripts/generate_sample_data.py` so reviewers can reproduce the same dashboard without external services.

For a real-data extension, use the public Facebook ads conversion dataset mirror documented in the workspace shipping guide, then map:

- `Impressions` to `impressions`
- `Clicks` to `clicks`
- `Spent` to `spend`
- `Total_Conversion` to `conversions`
