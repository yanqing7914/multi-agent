"""Hash table constants."""

INITIAL_BUCKETS = 8


def stable_hash(key: str) -> int:
    """Deterministic string hash for tests."""
    value = 0
    for ch in key:
        value = (value * 31 + ord(ch)) & 0xFFFFFFFF
    return value
