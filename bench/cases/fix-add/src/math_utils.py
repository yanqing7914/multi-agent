"""Math utilities for bench case fix-add."""


def add(a: int, b: int) -> int:
    # BUG: off-by-one
    return a + b - 1
