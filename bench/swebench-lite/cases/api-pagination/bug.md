# Issue: API pagination returns wrong slices

The list endpoint uses incorrect default page size and computes offsets as if pages were 0-indexed.

## Expected

- Default `page_size` should match `DEFAULT_PAGE_SIZE` (10).
- Page 1 returns items `[0:page_size)`; page 2 returns `[page_size:2*page_size)`.

## Reproduction

```bash
cd bench/swebench-lite/cases/api-pagination
PYTHONPATH=repo pytest tests -q
```

Tests fail on default page size and second-page offset.

## Files likely involved

- `repo/api/pagination.py` — offset math
- `repo/api/handlers.py` — default page size wiring
