class DataQualityError(Exception):
    """Raised when source data fails quality checks."""


class DataFreshnessError(Exception):
    """Raised when source data is older than the configured freshness window."""

