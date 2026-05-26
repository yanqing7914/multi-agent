from src.math_utils import add


def test_add_basic():
    assert add(2, 3) == 5


def test_add_zero():
    assert add(-1, 1) == 0
