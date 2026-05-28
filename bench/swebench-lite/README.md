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

## Recent live runtime results

### 2026-05-26 G2 full live run

Each row is one real runtime x case invocation with a 300s launcher timeout. `First real pass` means this artifact is the first archived live run for that runtime/case that reached `ok: true`.

| Timestamp (UTC) | Runtime | Case | Pass rate | Launcher status | First real pass | Artifact |
| --- | --- | --- | ---: | --- | --- | --- |
| 2026-05-26T08:39:46Z | codex | `api-pagination` | 0.0 | failed: launcher timeout after 300s | No; previous codex pass exists (`score-20260526-024848.json`) | `bench/swebench-lite/results/score-20260526-083946.json` |
| 2026-05-26T08:44:37Z | codex | `date-parse` | 0.0 | failed: launcher timeout after 300s | No | `bench/swebench-lite/results/score-20260526-084437.json` |
| 2026-05-26T08:49:29Z | codex | `hash-collision` | 0.0 | failed: launcher timeout after 300s | No | `bench/swebench-lite/results/score-20260526-084929.json` |
| 2026-05-26T08:50:42Z | cursor | `api-pagination` | 1.0 | completed: foreground tmux wait + audit OK | Yes | `bench/swebench-lite/results/score-20260526-085042.json` |
| 2026-05-26T08:52:14Z | cursor | `date-parse` | 1.0 | completed: foreground tmux wait + audit OK | Yes; earlier cursor live runs failed before launcher fix | `bench/swebench-lite/results/score-20260526-085214.json` |
| 2026-05-26T08:53:37Z | cursor | `hash-collision` | 1.0 | completed: foreground tmux wait + audit OK | Yes; earlier cursor live runs failed before launcher fix | `bench/swebench-lite/results/score-20260526-085337.json` |

### Earlier samples

| Timestamp (UTC) | Runtime | Cases | Pass rate | Artifact | Notes |
| --- | --- | ---: | ---: | --- | --- |
| 2026-05-26T02:48:48Z | codex | 1 (`api-pagination`) | 1.0 | `bench/swebench-lite/results/score-20260526-024848.json` | Regression pass after fixing outcome detection: complete JSON/Markdown reports are accepted even if diagnostic text mentions `timeout`; live-run changed paths are normalized to workspace-relative paths before audit. |
| 2026-05-26T02:14:11Z | codex | 1 (`api-pagination`) | 0.0 | `bench/swebench-lite/results/score-20260526-021411.json` | Legacy failed run: launcher outcome detection misclassified a completed Codex report as `timeout` because it scanned the whole transcript before validating result artifacts. |
| 2026-05-26T02:26:57Z | cursor | 1 (`date-parse`) | 0.0 | `bench/swebench-lite/results/score-20260526-022657.json` | Launcher spawn OK (`launch_cursor_worker.sh` tmux); harness did not wait for agent; pytest failed (3/4 tests). |
| 2026-05-26T02:27:44Z | cursor | 1 (`hash-collision`) | 0.0 | `bench/swebench-lite/results/score-20260526-022744.json` | Retry after duplicate `cursor-T002` session; spawn OK, pytest failed (1/3 tests). First attempt: `score-20260526-022704.json` (`launcher failed`). |

## Integration

Wired into `scripts/validate_all_adapters.py` as `swebench-lite` (dry `--self-check` only).

See also: [`bench/README.md`](../README.md), [`docs/roadmap.md`](../../docs/roadmap.md).

## Machine-readable latest summary

- Root summary: [`../../BENCHMARKS.md`](../../BENCHMARKS.md)
- Machine-readable summary: [`results/latest-summary.json`](results/latest-summary.json)

Codex live runs now support a longer timeout:

```bash
python3 bench/swebench-lite/run_swebench_lite.py --runtime codex --timeout 900
# or
SWEBENCH_LITE_TIMEOUT=900 python3 bench/swebench-lite/run_swebench_lite.py --runtime codex
```