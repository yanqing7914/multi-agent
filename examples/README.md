# 示例目录

本目录收录 multi-agent-coding 的**流程示例**与**端到端案例研究**。案例研究展示真实门控、结果报告与审计产物，可直接对照 OpenClaw v1 脚本复现。

## 流程示例（轻量）

| 文件 | 说明 |
| --- | --- |
| [`feature.md`](feature.md) | 多模块功能开发：Explorer → Worker → Reviewer → Verifier |
| [`bugfix.md`](bugfix.md) | 缺陷修复：先调研再受控实现 |
| [`review.md`](review.md) | 只读评审：多 Reviewer + `ssrd` 等 Skill |

## 案例研究（完整产物）

### [case-study-fizzbuzz](case-study-fizzbuzz/)

| 项 | 内容 |
| --- | --- |
| **场景** | 在小型 `FizzBuzz` 模块上狗食 OpenClaw v1 任务控制：验证 Explorer → Worker → Reviewer → Verifier 全门控可通过，并覆盖反虚假完成规则。 |
| **角色** | Explorer、Worker、Reviewer、Verifier（由 Main 按任务卡编排） |
| **关键产物** | `cards/` 任务卡、`results/` JSON+Markdown 结果报告、`summary/run-summary.md` 门控快照 |
| **详情** | [case-study-fizzbuzz/README.md](case-study-fizzbuzz/README.md) |

### [case-study-flask-cli](case-study-flask-cli/)

| 项 | 内容 |
| --- | --- |
| **场景** | 多文件「Flask 形态」CLI（stdlib：`http.server` + `argparse`），演示跨模块 Worker 范围与 Codex 运行时启动。 |
| **角色** | Explorer、Worker、Reviewer、Verifier；经 `scripts/run_multi_agent.py --runtime codex` 启动 Worker |
| **关键产物** | `app/` 与 `tests/` 源码、`task.yaml` 任务定义、运行后填充的 `cards/`、`results/`、`summary/` |
| **详情** | [case-study-flask-cli/README.md](case-study-flask-cli/README.md) |

## 相关链接

- OpenClaw 适配器：[adapters/openclaw/README.md](../adapters/openclaw/README.md)
- 基准 harness：[bench/README.md](../bench/README.md)
