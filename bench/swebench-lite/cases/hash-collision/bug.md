# Issue: Hash table loses values on bucket collisions

When two keys land in the same bucket, only the first stored value is retrievable. Indexing also uses Python's salted `hash()`, breaking deterministic tests.

## Expected

- Chained buckets return all keys that collide.
- Stable hashing is used for bucket index selection.

## Reproduction

```bash
cd bench/swebench-lite/cases/hash-collision
PYTHONPATH=repo pytest tests -q
```

## Files likely involved

- `repo/hash/bucket.py` — collision lookup
- `repo/hash/table.py` — index selection
