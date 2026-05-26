# Local SWE-style benchmark (not upstream SWE-bench)

This directory contains a **lightweight, offline** benchmark inspired by [SWE-bench Lite](https://www.swebench.com/) but intentionally **not** a fork of upstream SWE-bench.

## Why local / mock-ok

- **No network** — cases are handcrafted mini-repos under `cases/`.
- **Deterministic dry runtime** — `--dry-runtime` applies known fixes without spawning Codex/Cursor/Claude CLIs.
- **Same mission-control gates** — each case runs `create_task_cards.py`, worker launch (or dry fix), `sync`, `audit`, and `--summarize`.

## Cases

| Case | Bug | Validation |
| --- | --- | --- |
| `fix-add` | Off-by-one in `add()` | `pytest tests/test_math_utils.py` |
| `fix-reverse` | Broken string reverse | `pytest tests/test_text_utils.py` |
| `fix-fib` | Wrong Fibonacci base case | `pytest tests/test_sequence.py` |

## Run

```bash
# Self-check (no external CLIs)
python3 bench/run_bench.py --self-check --dry-runtime

# Single case with dry worker simulation
python3 bench/run_bench.py --runtime dry-runtime --case fix-add

# Real runtime (requires configured adapter)
python3 bench/run_bench.py --runtime codex --case fix-add
```

## Extend

1. Copy a case folder under `bench/cases/<name>/` with `README.md`, `src/`, and `tests/`.
2. Add a fix pattern to `FIXES` in `run_bench.py` for dry-runtime simulation.
3. Run `python3 bench/run_bench.py --self-check --dry-runtime`.

## Methodology

For each case the harness:

1. Copies the case into a temp workspace
2. Generates task cards via OpenClaw `create_task_cards.py`
3. Launches a worker (`scripts/run_multi_agent.py` or `--dry-runtime`)
4. Runs sync → audit → summarize
5. Runs pytest to report pass/fail

Pass = tests green **and** scope audit `ok: true` for the worker change set.
