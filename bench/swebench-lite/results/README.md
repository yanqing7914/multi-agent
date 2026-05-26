# SWE-bench Lite 运行历史

每次执行 `bench/swebench-lite/run_swebench_lite.py`（非 `--self-check` 的常规跑分）会在本目录追加一条**带时间戳**的聚合分数快照，便于对比趋势。

## 文件命名

```text
score-YYYYMMDD-HHMMSS.json
```

示例：`score-20260526-143022.json`

每条 JSON 包含 `runtime`、`aggregate`（用例数、通过数、聚合 pass rate）、`per_case` 明细，以及 `archived_at` UTC 时间。

## 其他产物

| 路径 | 说明 |
| --- | --- |
| `aggregate-score.json` | 最近一次运行的聚合分数（每次运行覆盖） |
| `../cases/<name>/` | 各用例在 `--no-persist` 关闭时复制的 cards/results/summary（按用例名分子目录） |

## 命令

```bash
# 离线自测（临时目录，默认不写本目录时间戳归档）
python3 bench/swebench-lite/run_swebench_lite.py --self-check

# 干跑分：写入 aggregate-score.json + score-<timestamp>.json
python3 bench/swebench-lite/run_swebench_lite.py --runtime dry-runtime

# 跳过时间戳归档（仍写 aggregate-score.json）
python3 bench/swebench-lite/run_swebench_lite.py --runtime dry-runtime --no-archive
```

## 自测记录（2026-05-26）

在仓库根目录执行：

```bash
python3 bench/swebench-lite/run_swebench_lite.py --runtime dry-runtime
```

预期：终端 JSON 含 `"score_archive": "bench/swebench-lite/results/score-....json"`，且本目录出现新的 `score-*.json`。

## Live runtime samples（cursor，2026-05-26）

| Timestamp (UTC) | Runtime | Case | Pass rate | Artifact | Launcher |
| --- | --- | --- | ---: | --- | --- |
| 2026-05-26T02:26:57Z | cursor | `date-parse` | 0.0 | `score-20260526-022657.json` | spawn OK (tmux); tests failed |
| 2026-05-26T02:27:04Z | cursor | `hash-collision` | 0.0 | `score-20260526-022704.json` | failed (`duplicate session: cursor-T002`) |
| 2026-05-26T02:27:44Z | cursor | `hash-collision` | 0.0 | `score-20260526-022744.json` | spawn OK (retry); tests failed |
