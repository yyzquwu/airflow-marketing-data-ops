from __future__ import annotations

import pandas as pd


OUTPUT_COLUMNS = [
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


def normalize_google_ads(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.rename(columns={"spend_micros": "spend"}).copy()
    normalized["source"] = "google_ads"
    normalized["spend"] = pd.to_numeric(normalized["spend"], errors="coerce") / 1_000_000
    return normalized


def normalize_spend_micros_source(df: pd.DataFrame, source: str) -> pd.DataFrame:
    normalized = df.rename(columns={"spend_micros": "spend"}).copy()
    normalized["source"] = source
    normalized["spend"] = pd.to_numeric(normalized["spend"], errors="coerce") / 1_000_000
    return normalized


def normalize_meta_ads(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.rename(
        columns={
            "date_start": "date",
            "actions_purchase": "conversions",
        }
    ).copy()
    normalized["source"] = "meta_ads"
    return normalized


def normalize_tiktok_ads(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.rename(
        columns={
            "stat_time_day": "date",
            "advertiser_id": "account_id",
            "conversion": "conversions",
        }
    ).copy()
    normalized["source"] = "tiktok_ads"
    return normalized


def normalize_standard_source(df: pd.DataFrame, source: str) -> pd.DataFrame:
    normalized = df.copy()
    normalized["source"] = source
    return normalized


def build_unified_campaign_daily(source_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    frames = [
        normalize_google_ads(source_frames["google_ads"]),
        normalize_meta_ads(source_frames["meta_ads"]),
        normalize_tiktok_ads(source_frames["tiktok_ads"]),
        normalize_spend_micros_source(source_frames["youtube_ads"], "youtube_ads"),
        normalize_standard_source(source_frames["microsoft_ads"], "microsoft_ads"),
        normalize_standard_source(source_frames["other_ads"], "other_ads"),
    ]
    unified = pd.concat(frames, ignore_index=True)

    metric_columns = ["impressions", "clicks", "spend", "conversions"]
    for column in metric_columns:
        unified[column] = pd.to_numeric(unified[column], errors="coerce").fillna(0)

    group_columns = ["date", "source", "account_id", "campaign_id", "campaign_name"]
    campaign_daily = (
        unified.groupby(group_columns, as_index=False)[metric_columns]
        .sum()
        .sort_values(["date", "source", "campaign_id"])
        .reset_index(drop=True)
    )

    campaign_daily["ctr"] = safe_divide(campaign_daily["clicks"], campaign_daily["impressions"])
    campaign_daily["cpc"] = safe_divide(campaign_daily["spend"], campaign_daily["clicks"])
    campaign_daily["cpa"] = safe_divide(campaign_daily["spend"], campaign_daily["conversions"])

    campaign_daily["spend"] = campaign_daily["spend"].round(2)
    campaign_daily["ctr"] = campaign_daily["ctr"].round(6)
    campaign_daily["cpc"] = campaign_daily["cpc"].round(4)
    campaign_daily["cpa"] = campaign_daily["cpa"].round(4)
    return campaign_daily[OUTPUT_COLUMNS]


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator.divide(denominator.where(denominator != 0)).fillna(0)
