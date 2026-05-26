"""HTTP-style list handler (stdlib only)."""

from .pagination import DEFAULT_PAGE_SIZE, page_offset


def list_items(items: list, page: int = 1, page_size: int | None = None) -> dict:
    """Return a page of items plus metadata."""
    size = page_size if page_size is not None else 20  # BUG: ignores DEFAULT_PAGE_SIZE
    if page < 1:
        raise ValueError("page must be >= 1")
    offset = page_offset(page, size)
    window = items[offset : offset + size]
    total = len(items)
    return {
        "items": window,
        "page": page,
        "page_size": size,
        "total": total,
        "has_more": offset + size < total,
    }
