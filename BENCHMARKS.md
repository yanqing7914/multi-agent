# Benchmark Summary

This file summarizes archived `bench/swebench-lite/results/score-*.json` runs. These cases are local SWE-bench Lite-shaped synthetic cases, not upstream SWE-bench leaderboard results.

## Current takeaways

- Cursor latest full live run passed all three cases (3/3).
- Codex latest full live run failed all three cases due launcher timeout after 300s.
- Codex has an earlier api-pagination success, so the current failure is timeout/runtime stability, not a universal harness failure.
- run_swebench_lite.py now supports --timeout and defaults Codex live runs to 900s for future reruns.

## Latest result by runtime and case

| Runtime | Case | Latest pass rate | OK | Error | Timeout | Artifact |
| --- | --- | ---: | --- | --- | ---: | --- |
| codex | `api-pagination` | 0.0 | false | launcher failed | 300 | `score-20260526-083946.json` |
| codex | `date-parse` | 0.0 | false | launcher failed | 300 | `score-20260526-084437.json` |
| codex | `hash-collision` | 0.0 | false | launcher failed | 300 | `score-20260526-084929.json` |
| cursor | `api-pagination` | 1.0 | true |  |  | `score-20260526-085042.json` |
| cursor | `date-parse` | 1.0 | true |  |  | `score-20260526-085214.json` |
| cursor | `hash-collision` | 1.0 | true |  |  | `score-20260526-085337.json` |
| dry | `api-pagination` | 1.0 | true |  |  | `score-20260526-003502.json` |
| dry | `date-parse` | 1.0 | true |  |  | `score-20260526-003502.json` |
| dry | `hash-collision` | 1.0 | true |  |  | `score-20260526-003502.json` |

## Best archived result by runtime and case

| Runtime | Case | Best pass rate | OK | Artifact |
| --- | --- | ---: | --- | --- |
| codex | `api-pagination` | 1.0 | true | `score-20260526-024848.json` |
| codex | `date-parse` | 0.0 | false | `score-20260526-084437.json` |
| codex | `hash-collision` | 0.0 | false | `score-20260526-084929.json` |
| cursor | `api-pagination` | 1.0 | true | `score-20260526-085042.json` |
| cursor | `date-parse` | 1.0 | true | `score-20260526-085214.json` |
| cursor | `hash-collision` | 1.0 | true | `score-20260526-085337.json` |
| dry | `api-pagination` | 1.0 | true | `score-20260526-003502.json` |
| dry | `date-parse` | 1.0 | true | `score-20260526-003502.json` |
| dry | `hash-collision` | 1.0 | true | `score-20260526-003502.json` |

## Codex failure diagnosis

- Latest Codex full run artifacts (`score-20260526-083946.json`, `score-20260526-084437.json`, `score-20260526-084929.json`) all fail at launcher level with `timeout after 300s`.
- Earlier Codex `api-pagination` artifact `score-20260526-024848.json` passed with tests and audit OK, proving the harness can accept successful Codex reports.
- The likely immediate cause is the benchmark harness timeout being too aggressive for live Codex worker sessions.
- Fix applied: `run_swebench_lite.py` now supports `--timeout` / `SWEBENCH_LITE_TIMEOUT` and defaults Codex live runs to 900 seconds.

Recommended rerun:

```bash
python3 bench/swebench-lite/run_swebench_lite.py --runtime codex --timeout 900
```

