"""Sequence utilities for bench case fix-fib."""


def fib(n: int) -> int:
    if n <= 1:
        return 1  # BUG: fib(0) should be 0
    return fib(n - 1) + fib(n - 2)
