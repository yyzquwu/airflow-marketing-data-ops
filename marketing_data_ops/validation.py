from __future__ import annotations

from datetime import date

import pandas as pd

from marketing_data_ops.exceptions import DataFreshnessError, DataQualityError


def validate_required_columns(df: pd.DataFrame, source: str, required_columns: list[str]) -> None:
    missing = sorted(set(required_columns) - set(df.columns))
    if missing:
        raise DataQualityError(f"{source} is missing required columns: {', '.join(missing)}")


def validate_non_empty(df: pd.DataFrame, source: str) -> None:
    if df.empty:
        raise DataQualityError(f"{source} extract is empty")


def validate_non_negative(df: pd.DataFrame, source: str, metric_columns: list[str]) -> None:
    available_metrics = [column for column in metric_columns if column in df.columns]
    for column in available_metrics:
        if (pd.to_numeric(df[column], errors="coerce") < 0).any():
            raise DataQualityError(f"{source}.{column} contains negative values")


def validate_freshness(
    df: pd.DataFrame,
    source: str,
    date_column: str,
    reference_date: date,
    max_lag_days: int,
) -> None:
    parsed_dates = pd.to_datetime(df[date_column], errors="coerce").dt.date
    if parsed_dates.isna().any():
        raise DataQualityError(f"{source}.{date_column} contains invalid dates")

    latest_date = max(parsed_dates)
    lag_days = (reference_date - latest_date).days
    if lag_days > max_lag_days:
        raise DataFreshnessError(
            f"{source} latest partition is {latest_date}; expected within {max_lag_days} days of {reference_date}"
        )


def validate_source(
    df: pd.DataFrame,
    source: str,
    required_columns: list[str],
    metric_columns: list[str],
    date_column: str,
    reference_date: date,
    max_lag_days: int,
) -> None:
    validate_non_empty(df, source)
    validate_required_columns(df, source, required_columns)
    validate_non_negative(df, source, metric_columns)
    validate_freshness(df, source, date_column, reference_date, max_lag_days)

