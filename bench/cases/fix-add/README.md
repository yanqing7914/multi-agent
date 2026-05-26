# Case: fix-add — off-by-one in add()

Fix the bug in `src/math_utils.py` so `add(a, b)` returns `a + b`.

## Spec

- `add(2, 3)` must return `5`
- `add(-1, 1)` must return `0`

## Validation

```bash
python3 -m pytest tests/test_math_utils.py -q
```

No network or dependency installation required.
