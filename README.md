# multi-agent

[![version](https://img.shields.io/badge/version-0.1.2-blue)](CHANGELOG.md)
[![python](https://img.shields.io/badge/python-%3E%3D3.10-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

`multi-agent` 是一个跨 IDE / 跨 Agent Runtime 的多 Agent 协作契约与任务控制框架。它面向 Codex、Cursor、Claude Code、OpenClaw/Her、Hermes 和 VS Code，目标是让不同 agent 围绕同一套任务卡、权限边界、结果报告、审计门控和评审规则协作。

它不是“开一堆 agent 自由发挥”的 swarm，而是一个 mission-control 风格的工程协作框架：

```text
Main Agent -> Task Card -> Worker / Reviewer / Verifier -> Result Report -> Scope Audit -> Final Delivery
```

## 项目定位

```text
Skill        = 协作方法论、角色规则和提示词规约
Adapters     = Codex / Cursor / Claude Code / OpenClaw 等运行时适配
Mission Core = task cards、ownership、status、audit、summary
Tools        = git/test/lint/shell/repo-index 的可审计 stdlib 封装
MCP          = 任务、状态、finding、审批和审计的工具后端
IDE Panel    = 图形化任务面板、Prompt 生成器和本地集成入口
```

## 直接下载 Skill 压缩包

如果只想安装 skill，不需要 clone 整个仓库，可以直接下载：

| 压缩包 | 适用场景 |
| --- | --- |
| [`codex-multi-agent-skill-v0.1.2.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.1.2/codex-multi-agent-skill-v0.1.2.zip) | Codex 专用，支持 Desktop handoff；有 CLI 时可自动 `codex exec` |
| [`cursor-multi-agent-pack-v0.1.2.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.1.2/cursor-multi-agent-pack-v0.1.2.zip) | Cursor 专用，包含 `cursor-rules.md` 与 `.cursor/rules/` |
| [`claude-code-multi-agent-pack-v0.1.2.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.1.2/claude-code-multi-agent-pack-v0.1.2.zip) | Claude Code 专用，包含 `CLAUDE.md` 与本地/ACP launcher |
| [`openclaw-multi-agent-skill-v0.1.2.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.1.2/openclaw-multi-agent-skill-v0.1.2.zip) | OpenClaw / Her 专用，推荐 OpenClaw 用户下载这个 |
| [`multi-agent-coding-skill-v0.1.2.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.1.2/multi-agent-coding-skill-v0.1.2.zip) | 通用协议包，只包含 skill 规则、模板和清单 |
| [`openclaw-multi-agent-skill-v0.1.1.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.1.1/openclaw-multi-agent-skill-v0.1.1.zip) | OpenClaw / Her 专用，推荐 OpenClaw 用户下载这个 |
| [`multi-agent-coding-skill-v0.1.1.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.1.1/multi-agent-coding-skill-v0.1.1.zip) | 通用 Codex/OpenClaw 风格 skill 包 |

安装方式：把这个 GitHub 链接发给你的 agent，并说“安装 multi-agent skill”。agent 应优先阅读 [`docs/agent-install.md`](docs/agent-install.md)，按自己的客户端选择对应包。
## 推荐入口

| 你是谁 | 推荐入口 |
| --- | --- |
| OpenClaw / Her 用户 | [`adapters/openclaw/QUICKSTART.md`](adapters/openclaw/QUICKSTART.md) |
| Cursor 用户 | [`adapters/cursor/QUICKSTART.md`](adapters/cursor/QUICKSTART.md) |
| Codex 用户 | [`adapters/codex/QUICKSTART.md`](adapters/codex/QUICKSTART.md) |
| Claude Code 用户 | [`adapters/claude-code/QUICKSTART.md`](adapters/claude-code/QUICKSTART.md) |
| 想看跨 IDE 真实接力证据 | [`.codex-multi-agent-relay/summary/run-summary.md`](.codex-multi-agent-relay/summary/run-summary.md) |
| 想看 MCP 协议 | [`mcp/multi-agent-coordinator/README.md`](mcp/multi-agent-coordinator/README.md) |
| 想让 agent 自动选择安装包 | [`docs/agent-install.md`](docs/agent-install.md) |
| 想看路线图 | [`docs/roadmap.md`](docs/roadmap.md) |
| 想看最新跑分摘要 | [BENCHMARKS.md](BENCHMARKS.md) |

## 当前能力概览

- **OpenClaw / Her：Production v1**，作为 mission-control 参考实现。
- **Cursor：可用并已 dogfood**，通过 launcher/tmux 接入 Worker runtime。
- **Codex：可用并已 dogfood**，需要 Codex CLI 和可写 sandbox。
- **Claude Code：契约已验证**，本地 quota/429 时建议走 OpenClaw ACP 路径。
- **MCP coordinator：v1 已有**，基于 `.codex-multi-agent/` 暴露任务、finding、审批和审计状态。
- **IDE panel：v1 已有雏形**，用于 mission-control task panel。
- **Bench / case studies：已有**，包括轻量 SWE-style cases、SWE-bench Lite-shaped cases、FizzBuzz 和 Flask CLI case study。

## 核心角色

| 角色 | 写权限 | 必须产出 |
| --- | --- | --- |
| Main | 有，但必须保护用户改动 | plan、task cards、audit、final delivery |
| Explorer | 无 | `files_read`、证据、风险、建议 |
| Worker | 仅限 `allowed_paths` | `files_changed`、JSON + Markdown result report |
| Reviewer | 无 | findings、severity、证据、建议 |
| Verifier | 默认无 | commands、validation、repro/test 结果 |

## 核心门控

项目重点不是相信 agent，而是检查 agent：

- `allowed_paths`：Worker 只能改授权路径。
- `required_paths_verified`：声称完成前必须确认关键路径可读。
- `files_read`：避免没读代码就完成的 thin evidence。
- `workspace_observed`：防止在错误 workspace 执行。
- `files_changed`：审计 Worker 是否越界。
- `tools_used`：声明使用过的框架工具。
- `scope_audit`：最终交付前检查违规、冲突、敏感路径和缺失报告。

## OpenClaw Adapter（v1 Mission Control）

OpenClaw/Her 用户可以只安装 [`adapters/openclaw/`](adapters/openclaw/) 作为 `openclaw-multi-agent` skill，不需要理解整个根仓库。

| 文件 | 用途 |
| --- | --- |
| `SKILL.md` | OpenClaw session workflow、角色边界、gate 规则 |
| `scripts/create_task_cards.py` | 生成 task cards、`ownership.json`、`status.json`、`run-plan.json` |
| `scripts/update_task_status.py` | 同步 gate、更新任务状态、生成 summary |
| `scripts/audit_worker_output.py` | scope audit，并可写入 `audits/` |
| `scripts/run_local_demo.py` | 确定性本地 demo 和 `--self-check` |
| `QUICKSTART.md` | 新 clone 后的 Golden Path |

快速验证：

```bash
cd adapters/openclaw
python3 scripts/validate_all.py
```

完整验证：

```bash
make validate
# or
python3 scripts/validate_all_adapters.py
bash scripts/full_validate.sh
```

## 跨 Adapter Launcher

所有 client adapter 尽量复用 OpenClaw mission-control core，不复制 gate 逻辑。

```bash
python3 scripts/run_multi_agent.py --runtime cursor|codex|claude-code|openclaw --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Launcher 使用 `pipefail` 和 post-run checks：外部 CLI 失败、quota/error pattern、结果 Markdown 过薄、JSON 缺失等都应该返回非零和 `"ok": false`。

## Tools Layer

`tools/` 下提供 dependency-free stdlib wrappers，供 Worker/Verifier 声明式使用：

| Tool | Purpose |
| --- | --- |
| `git_tool.py` | `git status`、`diff`、changed files |
| `test_runner_tool.py` | 发现并运行 `pytest`、`npm test`、`pnpm test` |
| `lint_tool.py` | best-effort lint / format / type check |
| `shell_tool.py` | allowlist/denylist shell wrapper |
| `repo_index_tool.py` | 文件列表和 grep，`rg` 不可用时 fallback |

每个工具支持 `--help`、JSON-in/JSON-out 和 `--self-check`。

## Memory Layer

- [`MEMORY.md`](MEMORY.md)：append-only 项目决策和运行摘要，不保存 secret。
- [`AGENTS.md`](AGENTS.md)：repo-wide 角色约定和安全 gate。
- `memory_log.py` / `memory_rotate.py`：用于记录和轮转运行记忆。

最新 memory tail 会注入 task card 的 `context`，帮助 Worker 避免重复踩坑。

## Bench 与 Case Studies

- [`bench/`](bench/)：轻量 SWE-style cases。
- [`bench/swebench-lite/`](bench/swebench-lite/)：SWE-bench Lite-shaped 多文件 cases。
- [`examples/case-study-fizzbuzz/`](examples/case-study-fizzbuzz/)：all gates green case study。
- [`examples/case-study-flask-cli/`](examples/case-study-flask-cli/)：多文件 Flask-shaped CLI case study。
- [`.codex-multi-agent-relay/`](.codex-multi-agent-relay/)：跨 IDE 接力 demo 公开凭证。

自检：

```bash
python3 bench/run_bench.py --self-check --dry-runtime
python3 bench/swebench-lite/run_swebench_lite.py --self-check
```

## 跨 IDE 接力 Demo

最新 recorded demo 展示了三家 IDE / runtime 的端到端接力：

```text
OpenClaw Main -> Cursor Worker -> Claude Code Reviewer -> OpenClaw Scope Audit
```

证据链保存在 `.codex-multi-agent-relay/`：

- `ownership.json`
- `run-plan.json`
- `tasks/`
- `results/`
- `audits/latest.json`
- `summary/run-summary.md`
- `changed-files.txt`

复验：

```bash
python3 adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent-relay/ownership.json \
  --results .codex-multi-agent-relay/results \
  --changed-files .codex-multi-agent-relay/changed-files.txt
```

## MCP 与 IDE

- MCP coordinator server：[`mcp/multi-agent-coordinator/`](mcp/multi-agent-coordinator/)
- Per-client MCP config snippets：[`mcp/multi-agent-coordinator/clients/`](mcp/multi-agent-coordinator/clients/)
- Mission-control task panel：[`ide/multi-agent-panel/`](ide/multi-agent-panel/)
- VS Code / Cursor / Hermes extension scaffolds：[`ide/extensions/`](ide/extensions/)

## 什么时候使用多 Agent

适合：

- 多模块 feature / refactor。
- 复杂 bug investigation。
- 需要 Explorer、Worker、Reviewer、Verifier 分离的任务。
- 多视角评审、安全审查、SSRD review。
- 跨 IDE / runtime 接力。

不适合：

- 单文件小改动。
- 明确的小 bug。
- 简单解释代码。
- 没有安全 ownership 边界的任务。

## 路线图

```text
v1 scripts：OpenClaw mission-control core + adapters + audit gates
v2 MCP：任务、状态、finding、approval、audit 的工具后端
v3 IDE panel：任务面板、Prompt 生成器、审计视图
v4 worktree / PR / CI：并行分支、PR review、CI 失败回流
```
