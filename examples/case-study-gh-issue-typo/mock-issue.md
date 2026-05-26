# [docs] Typo in `parse_retry_after` docstring ("retrun")

**Labels:** `bug`, `good first issue`, `documentation`

## Reported by

@reader-dev — 2026-05-20

## Description

While integrating retry backoff helpers I noticed the docstring for `parse_retry_after` says the function will *"retrun None"* when the header is missing. Pretty sure that should be **return**.

```python
>>> import retry_utils
>>> help(retry_utils.parse_retry_after)
...
```

Screenshot in thread shows the typo on line 12 of `retry_utils.py`.

## Expected

Docstring uses correct spelling: **return**.

## Actual

Docstring contains `retrun`.

## Environment

- Python 3.11+
- `retry_utils` 0.4.2 (example package — this case study uses `before.py` as a stand-in)

## Acceptance criteria

- [ ] Fix typo in docstring only (no behavior change)
- [ ] `python3 -m py_compile retry_utils.py` passes
