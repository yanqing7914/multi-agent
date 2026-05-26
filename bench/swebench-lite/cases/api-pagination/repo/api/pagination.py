"""Pagination helpers."""

DEFAULT_PAGE_SIZE = 10


def page_offset(page: int, page_size: int) -> int:
    """Return slice offset for 1-indexed page numbers."""
    # BUG: treats page as 0-indexed
    return page * page_size
