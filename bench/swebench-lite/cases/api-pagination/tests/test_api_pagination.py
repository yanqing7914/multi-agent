import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1] / "repo"
sys.path.insert(0, str(REPO))

from api.handlers import list_items  # noqa: E402
from api.pagination import DEFAULT_PAGE_SIZE  # noqa: E402


def test_default_page_size():
    data = list_items(list(range(30)), page=1)
    assert data["page_size"] == DEFAULT_PAGE_SIZE


def test_first_page_offset():
    items = [f"item-{i}" for i in range(25)]
    data = list_items(items, page=1, page_size=10)
    assert data["items"] == items[:10]
    assert data["has_more"] is True


def test_second_page_offset():
    items = [f"item-{i}" for i in range(25)]
    data = list_items(items, page=2, page_size=10)
    assert data["items"] == items[10:20]
