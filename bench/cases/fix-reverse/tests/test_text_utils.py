from src.text_utils import reverse_text


def test_reverse_basic():
    assert reverse_text("abc") == "cba"


def test_reverse_empty():
    assert reverse_text("") == ""
