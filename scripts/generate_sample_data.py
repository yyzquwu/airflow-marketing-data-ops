from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
START_DATE = date(2025, 4, 18)
END_DATE = date(2025, 5, 18)
PLATFORM_TOTAL_SPEND = {
    "meta_ads": 1_587_432.00,
    "google_ads": 1_284_915.00,
    "tiktok_ads": 732_418.00,
    "youtube_ads": 367_229.00,
    "microsoft_ads": 154_748.00,
    "other_ads": 112_000.00,
}
PLATFORM_NAME = {
    "meta_ads": "Meta",
    "google_ads": "Google",
    "tiktok_ads": "TikTok",
    "youtube_ads": "YouTube",
    "microsoft_ads": "Microsoft",
    "other_ads": "Other",
}


@dataclass(frozen=True)
class PlatformProfile:
    source: str
    account_id: str
    prefix: str
    ctr: float
    cpc: float
    cpa: float


PLATFORMS = {
    "meta_ads": PlatformProfile("meta_ads", "act_998877", "m", 0.0153, 0.79, 50.7),
    "google_ads": PlatformProfile("google_ads", "111-222-3333", "g", 0.0137, 0.85, 60.5),
    "tiktok_ads": PlatformProfile("tiktok_ads", "tt_445566", "t", 0.0171, 0.96, 84.8),
    "youtube_ads": PlatformProfile("youtube_ads", "yt_776655", "y", 0.0107, 1.11, 78.7),
    "microsoft_ads": PlatformProfile("microsoft_ads", "ms_334455", "ms", 0.0099, 1.20, 110.4),
    "other_ads": PlatformProfile("other_ads", "ot_221144", "o", 0.0085, 1.30, 129.1),
}

FEATURED_CAMPAIGNS = [
    ("meta_ads", "Paramount+ Spring Promo"),
    ("google_ads", "Top Gun: Maverick Push"),
    ("meta_ads", "Yellowstone S5 Launch"),
    ("youtube_ads", "Star Trek: Strange New Worlds"),
    ("tiktok_ads", "Halo S2 Campaign"),
    ("tiktok_ads", "Teen Wolf: The Movie"),
    ("meta_ads", "PAW Patrol: The Mighty Movie"),
    ("google_ads", "Transformers: Rise of the Beasts"),
    ("microsoft_ads", "Mission: Impossible - Dead Reckoning"),
    ("other_ads", "iCarly Reboot Awareness"),
]

FRANCHISES = [
    "Paramount+ Originals",
    "Drama Collection",
    "Comedy Classics",
    "Sports Weekend",
    "Kids and Family",
    "Reality Launch",
    "Sci-Fi Vault",
    "Movie Night",
    "Holiday Watchlist",
    "Live Events",
    "Library Retention",
    "Premium Bundle",
    "Student Offer",
    "Family Plan",
    "Winback Audience",
    "New Release",
    "Binge Weekend",
    "Award Season",
    "Streaming Trial",
    "International Pack",
]
OBJECTIVES = ["Awareness", "Prospecting", "Retargeting", "Trial", "Winback"]
REGIONS = ["US", "West", "East", "Midwest", "South"]
PLATFORM_CAMPAIGN_COUNTS = {
    "meta_ads": 28,
    "google_ads": 25,
    "tiktok_ads": 18,
    "youtube_ads": 12,
    "microsoft_ads": 8,
    "other_ads": 6,
}


def date_range(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def build_campaigns() -> list[dict[str, object]]:
    campaigns: list[dict[str, object]] = []
    counters = {source: 0 for source in PLATFORMS}

    for source, name in FEATURED_CAMPAIGNS:
        counters[source] += 1
        profile = PLATFORMS[source]
        campaigns.append(
            {
                "source": source,
                "campaign_id": f"{profile.prefix}-{counters[source]:04d}",
                "campaign_name": name,
                "priority": 3.0 - (0.12 * (counters[source] % 5)),
            }
        )

    for source, target_count in PLATFORM_CAMPAIGN_COUNTS.items():
        profile = PLATFORMS[source]
        while counters[source] < target_count:
            idx = counters[source]
            name = (
                f"{FRANCHISES[idx % len(FRANCHISES)]} "
                f"{OBJECTIVES[idx % len(OBJECTIVES)]} "
                f"{REGIONS[idx % len(REGIONS)]} "
                f"{PLATFORM_NAME[source]}"
            )
            if name in {campaign["campaign_name"] for campaign in campaigns}:
                name = f"{name} {idx + 1}"
            counters[source] += 1
            campaigns.append(
                {
                    "source": source,
                    "campaign_id": f"{profile.prefix}-{counters[source]:04d}",
                    "campaign_name": name,
                    "priority": 1.0 + ((idx % 9) * 0.13),
                }
            )
    return campaigns


def normalized(values: list[float]) -> list[float]:
    total = sum(values)
    return [value / total for value in values]


def day_weights(days: list[date]) -> list[float]:
    weights = []
    for idx, day in enumerate(days):
        weekday_lift = 1.12 if day.weekday() in {4, 5, 6} else 1.0
        pulse = 1.28 if idx in {4, 11, 17, 25} else 1.0
        ramp = 0.92 + (idx / max(len(days) - 1, 1)) * 0.18
        weights.append(weekday_lift * pulse * ramp)
    return normalized(weights)


def campaign_weights(campaigns: list[dict[str, object]]) -> dict[str, float]:
    raw = {str(campaign["campaign_id"]): float(campaign["priority"]) for campaign in campaigns}
    total = sum(raw.values())
    return {campaign_id: value / total for campaign_id, value in raw.items()}


def build_rows() -> dict[str, list[dict[str, object]]]:
    days = date_range(START_DATE, END_DATE)
    by_source: dict[str, list[dict[str, object]]] = {source: [] for source in PLATFORMS}
    campaigns = build_campaigns()

    for source in PLATFORMS:
        source_campaigns = [campaign for campaign in campaigns if campaign["source"] == source]
        c_weights = campaign_weights(source_campaigns)
        d_weights = day_weights(days)
        profile = PLATFORMS[source]
        platform_spend = PLATFORM_TOTAL_SPEND[source]

        for day_idx, day in enumerate(days):
            for campaign in source_campaigns:
                campaign_id = str(campaign["campaign_id"])
                spend = platform_spend * d_weights[day_idx] * c_weights[campaign_id]
                efficiency_lift = 1 + (((day_idx + len(campaign_id)) % 7) - 3) * 0.018
                clicks = max(1, round((spend / profile.cpc) * efficiency_lift))
                conversions = max(1, round((spend / profile.cpa) * (2 - efficiency_lift)))
                impressions = max(clicks, round(clicks / profile.ctr))

                by_source[source].append(
                    {
                        "date": day.isoformat(),
                        "account_id": profile.account_id,
                        "campaign_id": campaign_id,
                        "campaign_name": campaign["campaign_name"],
                        "impressions": impressions,
                        "clicks": clicks,
                        "spend": round(spend, 2),
                        "spend_micros": round(spend * 1_000_000),
                        "conversions": conversions,
                    }
                )
    return by_source


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{field: row[field] for field in fieldnames} for row in rows])


def main() -> None:
    rows = build_rows()
    write_csv(
        PROJECT_ROOT / "data/raw/google_ads/campaign_daily.csv",
        ["date", "account_id", "campaign_id", "campaign_name", "impressions", "clicks", "spend_micros", "conversions"],
        rows["google_ads"],
    )
    write_csv(
        PROJECT_ROOT / "data/raw/meta_ads/campaign_daily.csv",
        ["date_start", "account_id", "campaign_id", "campaign_name", "impressions", "clicks", "spend", "actions_purchase"],
        [
            {
                **row,
                "date_start": row["date"],
                "actions_purchase": row["conversions"],
            }
            for row in rows["meta_ads"]
        ],
    )
    write_csv(
        PROJECT_ROOT / "data/raw/tiktok_ads/campaign_daily.csv",
        ["stat_time_day", "advertiser_id", "campaign_id", "campaign_name", "impressions", "clicks", "spend", "conversion"],
        [
            {
                **row,
                "stat_time_day": row["date"],
                "advertiser_id": row["account_id"],
                "conversion": row["conversions"],
            }
            for row in rows["tiktok_ads"]
        ],
    )
    write_csv(
        PROJECT_ROOT / "data/raw/youtube_ads/campaign_daily.csv",
        ["date", "account_id", "campaign_id", "campaign_name", "impressions", "clicks", "spend_micros", "conversions"],
        rows["youtube_ads"],
    )
    write_csv(
        PROJECT_ROOT / "data/raw/microsoft_ads/campaign_daily.csv",
        ["date", "account_id", "campaign_id", "campaign_name", "impressions", "clicks", "spend", "conversions"],
        rows["microsoft_ads"],
    )
    write_csv(
        PROJECT_ROOT / "data/raw/other_ads/campaign_daily.csv",
        ["date", "account_id", "campaign_id", "campaign_name", "impressions", "clicks", "spend", "conversions"],
        rows["other_ads"],
    )


if __name__ == "__main__":
    main()
