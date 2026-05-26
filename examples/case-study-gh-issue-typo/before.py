"""Minimal retry header helper (case-study sample; not a published package)."""

from __future__ import annotations


def parse_retry_after(header_value: str | None) -> int | None:
    """Parse a Retry-After header value into seconds.

    Accepts integer seconds or HTTP-date form. If the header is missing or
    unparsable, retrun None.
    """
    if header_value is None:
        return None
    value = header_value.strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    return None
