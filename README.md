# multi-agent

[![version](https://img.shields.io/badge/version-0.2.0-blue)](CHANGELOG.md)
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
| [`codex-multi-agent-skill-v0.2.0.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.2.0/codex-multi-agent-skill-v0.2.0.zip) | Codex App + CLI 原生 skill，包含 Codex custom agents 与 `codex exec` bridge |
| [`cursor-multi-agent-pack-v0.2.0.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.2.0/cursor-multi-agent-pack-v0.2.0.zip) | Cursor App + CLI 原生 skill，完整 Worker 自动化通过本机 `agent` CLI bridge |
| [`claude-code-multi-agent-pack-v0.2.0.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.2.0/claude-code-multi-agent-pack-v0.2.0.zip) | Claude Code App/IDE + CLI 原生 skill，包含 Claude subagents 与 CLI bridge |
| [`openclaw-multi-agent-skill-v0.2.0.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.2.0/openclaw-multi-agent-skill-v0.2.0.zip) | OpenClaw / Her 专用，推荐 OpenClaw 用户下载这个 |
| [`multi-agent-coding-skill-v0.2.0.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.2.0/multi-agent-coding-skill-v0.2.0.zip) | 通用协议包，只包含共享 skill 规则、模板和清单；原生安装请使用客户端专用包 |

安装方式：把这个 GitHub 链接发给你的 agent，并说“安装 multi-agent skill”。agent 应优先阅读 [`docs/agent-install.md`](docs/agent-install.md)，按自己的客户端选择对应包。

## v0.2.0 完整支持标准

“完整使用”不是只生成 prompt，而是同一套 skill 在 App 和 CLI 中都能完成：

1. 原生发现 skill：App/CLI 启动后能在自己的 skill 系统里看到并触发。
2. 生成任务卡：Main 创建 `.codex-multi-agent/tasks/*.md`、`ownership.json`、`status.json`。
3. 安排 Worker/Reviewer/Verifier：优先原生 subagent；没有原生 subagent API 的客户端使用本机 CLI bridge。
4. 约束权限：`allowed_paths`、`blocked_commands`、`may_use_skills`、只读 Reviewer。
5. 回收结果：每个 agent 写 JSON + Markdown result report。
6. 审计交付：Main 跑 gate sync、scope audit，再 final delivery。

| 客户端 | App 完整模式 | CLI 完整模式 | Worker 编排方式 | 备注 |
| --- | --- | --- | --- | --- |
| Codex | ✅ 原生 skill + 原生 subagents | ✅ 原生 skill + subagents / `codex exec` | native subagent 或 `--runtime codex` | Codex App/CLI 都支持 skills；subagents 默认可用 |
| Cursor | ✅ 原生 skill + `agent` CLI bridge | ✅ 原生 skill + `agent -p` | `--runtime cursor`，tmux/foreground 回收报告 | Cursor App 支持 skills，但没有公开等价 native subagent API；完整自动化需要本机 `agent` CLI |
| Claude Code | ✅ 原生 skill + Claude subagents | ✅ 原生 skill + Claude subagents / `claude --print` | `.claude/agents` 或 `--runtime claude-code` | Claude Code App/IDE 扩展内置 CLI 面板；独立终端自动化需 standalone `claude` |

如果某台机器缺少 CLI bridge，项目不再宣称“完整自动化”；只能使用 prompt handoff 降级路径。

## 一键原生安装 / 检查

从解压后的包根目录运行：

```bash
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check
```

`--scope primary` 安装到每个客户端推荐的原生 skill 目录。`--scope all-compatible` 会同时写入兼容目录，例如 `.agents/skills`、`.cursor/skills`、`.claude/skills`、`.codex/skills`。

## 推荐入口

| 你是谁 | 推荐入口 |
| --- | --- |
| OpenClaw / Her 用户 | [`adapters/openclaw/QUICKSTART.md`](adapters/openclaw/QUICKSTART.md) |
| Cursor App / CLI 用户 | [`adapters/cursor/QUICKSTART.md`](adapters/cursor/QUICKSTART.md) |
| Codex App / CLI 用户 | [`adapters/codex/QUICKSTART.md`](adapters/codex/QUICKSTART.md) |
| Claude Code App / CLI 用户 | [`adapters/claude-code/QUICKSTART.md`](adapters/claude-code/QUICKSTART.md) |
| 想看自动安装入口 | [`docs/agent-install.md`](docs/agent-install.md) |
| 想看 MCP 协议 | [`mcp/multi-agent-coordinator/README.md`](mcp/multi-agent-coordinator/README.md) |
| 想看路线图 | [`docs/roadmap.md`](docs/roadmap.md) |
| 想看最新跑分摘要 | [BENCHMARKS.md](BENCHMARKS.md) |

## 当前能力概览

- **Codex：完整 v0.2**，App/CLI 原生 skill + 原生 subagents，CLI bridge 走 `codex exec`。
- **Cursor：完整 v0.2（带 bridge 条件）**，App/CLI 原生 skill；完整 Worker 自动化需要本机 `agent` CLI。
- **Claude Code：完整 v0.2**，App/IDE/CLI 原生 skill + `.claude/agents` subagents，CLI bridge 走 `claude --print`。
- **OpenClaw / Her：Production v1**，作为 mission-control 参考实现。
- **MCP coordinator：v1 已有**，基于 `.codex-multi-agent/` 暴露任务、finding、审批和审计状态。
- **IDE panel：v1 已有雏形**，用于 mission-control task panel。
- **Bench / case studies：已有**，包括轻量 SWE-style cases、SWE-bench Lite-shaped cases、FizzBuzz、Flask CLI 和 GitHub-link 安装端到端 demo。

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
python3 scripts/run_multi_agent.py --runtime cursor-desktop|cursor|codex-native|codex-desktop|codex|claude-desktop|claude-code|openclaw --task-card .codex-multi-agent/tasks/T002-worker-backend.md
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
