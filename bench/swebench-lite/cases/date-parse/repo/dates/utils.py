"""Timezone helpers."""

from datetime import datetime, timezone


def to_utc(dt: datetime) -> datetime:
    """Normalize datetimes to UTC."""
    # BUG: naive datetimes pass through unchanged
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc)
