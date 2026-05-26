from src.sequence import fib


def test_fib_base():
    assert fib(0) == 0
    assert fib(1) == 1


def test_fib_fifth():
    assert fib(5) == 5
