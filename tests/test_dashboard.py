from __future__ import annotations

import pandas as pd

from dashboard.app import prepare_campaign_data, summarize_performance


def test_dashboard_prepares_mixed_output_dates() -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-05-03 00:00:00", "2026-05-04"],
            "source": ["google_ads", "meta_ads"],
            "account_id": ["a1", "a2"],
            "campaign_id": ["c1", "c2"],
            "campaign_name": ["Brand", "Prospecting"],
            "impressions": [100, 200],
            "clicks": [10, 20],
            "spend": [25.0, 50.0],
            "conversions": [5, 10],
            "ctr": [0.1, 0.1],
            "cpc": [2.5, 2.5],
            "cpa": [5.0, 5.0],
        }
    )

    prepared = prepare_campaign_data(df)
    summary = summarize_performance(prepared)

    assert prepared["date"].isna().sum() == 0
    assert prepared["source_label"].tolist() == ["Google Ads", "Meta Ads"]
    assert summary["spend"] == 75.0
    assert summary["conversions"] == 15.0
    assert summary["cpa"] == 5.0
