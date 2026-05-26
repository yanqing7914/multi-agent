# Case: fix-fib — wrong base case

Fix `fib(n)` in `src/sequence.py` so Fibonacci numbers match the spec.

## Spec

- `fib(0) == 0`, `fib(1) == 1`, `fib(5) == 5`

## Validation

```bash
python3 -m pytest tests/test_sequence.py -q
```
