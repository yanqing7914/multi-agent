# Issue: Date parser misses ISO format and UTC normalization

Users report ISO dates (`YYYY-MM-DD`) are not parsed and naive datetimes are not tagged as UTC.

## Expected

- `parse_date("2024-03-15")` succeeds.
- Invalid input raises `ValueError`.
- `to_utc(naive_dt)` returns UTC-aware datetime.

## Reproduction

```bash
cd bench/swebench-lite/cases/date-parse
PYTHONPATH=repo pytest tests -q
```

## Files likely involved

- `repo/dates/formats.py`
- `repo/dates/parser.py`
- `repo/dates/utils.py`
