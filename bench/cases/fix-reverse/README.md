# Case: fix-reverse — broken string reverse

Fix `reverse_text` in `src/text_utils.py`.

## Spec

- `reverse_text("abc")` → `"cba"`
- `reverse_text("")` → `""`

## Validation

```bash
python3 -m pytest tests/test_text_utils.py -q
```
