# SWE-bench Lite-style offline benchmark

Lightweight, **local** benchmark cases shaped like [SWE-bench Lite](https://www.swebench.com/) instances — but **not** upstream SWE-bench.

## Why this is NOT upstream SWE-bench

| Aspect | Upstream SWE-bench Lite | This harness |
| --- | --- | --- |
| Repos | Real open-source snapshots | Tiny synthetic multi-file `repo/` trees |
| Evaluation | Docker + LLM patch application | Local pytest pass-rate + mission-control audit |
| Dependencies | Full project installs | Stdlib-only Python + pytest |
| Patch source | Model-generated | `golden_patch.diff` reference (self-check) or live runtime |

This benchmark validates **multi-file repair workflows** and mission-control integration, not model leaderboard scores.

## Case layout

Each case under `cases/<name>/`:

```text
cases/api-pagination/
  bug.md              # Issue spec (like a GitHub issue)
  golden_patch.diff   # Reference fix for evaluator / --self-check
  repo/               # Broken snapshot (>3 files)
  tests/              # Real pytest suite
```

Current cases:

- `api-pagination` — default page size + offset math across `handlers.py` / `pagination.py`
- `date-parse` — ISO format, error handling, UTC normalization across `formats.py` / `parser.py` / `utils.py`
- `hash-collision` — chaining + stable hash across `bucket.py` / `table.py`

## Mapping to SWE-bench Lite shape

| SWE-bench Lite field | Local equivalent |
| --- | --- |
| `problem_statement` | `bug.md` |
| `repo` snapshot | `repo/` directory |
| `test_patch` / tests | `tests/` (pytest) |
| `patch` (gold) | `golden_patch.diff` |
| Instance id="case name (`api-pagination`, …) |

## Run

```bash
# Deterministic self-check (applies golden_patch.diff, no LLM)
python3 bench/swebench-lite/run_swebench_lite.py --self-check

# Dry runtime (default) — same as self-check but writes results/
python3 bench/swebench-lite/run_swebench_lite.py --runtime dry

# Live runtime (requires external CLI)
python3 bench/swebench-lite/run_swebench_lite.py --runtime codex|cursor|claude|openclaw
```

## Outputs

Per case under `bench/swebench-lite/results/<case>/`:

- `cards/` — generated task cards
- `results/` — worker JSON/Markdown
- `summary/` — run summary
- `audit/` — scope audit JSON
- `score.json` — pytest pass-rate + audit status

Aggregate: `bench/swebench-lite/results/aggregate-score.json`

## Score

- **Per case:** `post_pass_rate` = 1.0 when pytest exits 0 after patch, else 0.0
- **Aggregate:** mean pass-rate across all cases

## Integration

Wired into `scripts/validate_all_adapters.py` as `swebench-lite` (dry `--self-check` only).

See also: [`bench/README.md`](../README.md), [`docs/roadmap.md`](../../docs/roadmap.md).
