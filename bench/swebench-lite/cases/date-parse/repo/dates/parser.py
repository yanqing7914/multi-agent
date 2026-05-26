"""Parse user-facing date strings."""

from datetime import datetime

from .formats import SUPPORTED_FORMATS


def parse_date(text: str) -> datetime:
    """Parse a date string using known formats."""
    for fmt in SUPPORTED_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    # BUG: returns None instead of raising
    return None  # type: ignore[return-value]
