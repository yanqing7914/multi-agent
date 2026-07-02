# multi-agent

[![version](https://img.shields.io/badge/version-0.3.1-blue)](CHANGELOG.md)
[![python](https://img.shields.io/badge/python-%3E%3D3.10-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

`multi-agent` 是一个跨 IDE / 跨 Agent Runtime 的多 Agent 协作契约与任务控制框架。它面向 Codex、Cursor、Claude Code、OpenClaw/Her、Hermes 和 VS Code，目标是让不同 agent 围绕同一套任务卡、权限边界、结果报告、审计门控和评审规则协作。

对 Codex 用户，`multi-agent` 本身就是日常主入口：它会直接走 Codex fast path（native subagents → `codex exec` bridge → manual handoff），而不是要求用户先切换到另一个 Codex-only skill。`adapters/codex/` 是 `multi-agent` 内置的 Codex 实现层。

它不是“开一堆 agent 自由发挥”的 swarm，而是一个 mission-control 风格的工程协作框架：

```text
Main Agent -> Task Card -> Worker / Reviewer / Verifier -> Result Report -> Scope Audit -> Final Delivery
```

## 项目定位

```text
Skill        = 协作方法论、角色规则和提示词规约
Adapters     = Codex / Cursor / Claude Code / OpenClaw / Hermes 等运行时适配
Mission Core = task cards、ownership、status、audit、summary
Tools        = git/test/lint/shell/repo-index 的可审计 stdlib 封装
MCP          = 任务、状态、finding、审批和审计的工具后端
IDE Panel    = 图形化任务面板、Prompt 生成器和本地集成入口
```

## 直接下载 Skill 压缩包

如果只想安装 skill，不需要 clone 整个仓库，可以直接下载：

| 压缩包 | 适用场景 |
| --- | --- |
| [`codex-multi-agent-skill-v0.3.1.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.3.1/codex-multi-agent-skill-v0.3.1.zip) | Codex App + CLI 原生 skill，包含 Codex custom agents 与 `codex exec` bridge |
| [`cursor-multi-agent-pack-v0.3.1.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.3.1/cursor-multi-agent-pack-v0.3.1.zip) | Cursor App + CLI 原生 skill，含 headless / `@cursor/sdk` 原生编排与本机 `agent` CLI bridge |
| [`claude-code-multi-agent-pack-v0.3.1.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.3.1/claude-code-multi-agent-pack-v0.3.1.zip) | Claude Code App/IDE + CLI 原生 skill，包含 Claude subagents、Agent Teams 映射与 CLI bridge |
| [`hermes-multi-agent-pack-v0.3.1.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.3.1/hermes-multi-agent-pack-v0.3.1.zip) | Hermes 专用，agentskills.io 可移植 skill + 原生 MCP（`~/.hermes/config.yaml`） |
| [`openclaw-multi-agent-skill-v0.3.1.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.3.1/openclaw-multi-agent-skill-v0.3.1.zip) | OpenClaw / Her 专用，推荐 OpenClaw 用户下载这个 |
| [`multi-agent-coding-skill-v0.3.1.zip`](https://github.com/yanqing7914/multi-agent/releases/download/v0.3.1/multi-agent-coding-skill-v0.3.1.zip) | 通用协议包，只包含共享 skill 规则、模板和清单；原生安装请使用客户端专用包 |

安装方式：把这个 GitHub 链接发给你的 agent，并说“安装 multi-agent skill”。agent 应优先阅读 [`docs/agent-install.md`](docs/agent-install.md)，按自己的客户端选择对应包。

开发、CI/CD、分支和发布流程见 [`docs/development.md`](docs/development.md)，仓库治理与评审规则见 [`docs/governance.md`](docs/governance.md)。项目按产品化流程维护：PR 必须过 fast CI，`main` 发布前跑 full CI，`vX.Y.Z` tag 触发 release zip 构建与包内容校验。
产品定义、能力边界和 v1.0 验收标准见 [`docs/product.md`](docs/product.md)。内容开放边界、开发者文档和 release zip 禁带规则见 [`docs/content-governance.md`](docs/content-governance.md)。一句话：客户端专用 zip 是用户安装入口，根仓库是源码、协议和发布工程。

## v0.3.1 完整支持标准

“完整使用”不是只生成 prompt，而是同一套 skill 在 App 和 CLI 中都能完成：

1. 原生发现 skill：App/CLI 启动后能在自己的 skill 系统里看到并触发。
2. 生成任务卡：Main 创建 `.codex-multi-agent/tasks/*.md`、`ownership.json`、`status.json`。
3. 安排 Worker/Reviewer/Verifier：优先使用客户端原生 subagent 能力；当原生集成尚未接入本适配器时，使用本机 CLI bridge 作为确定性自动化路径。
4. 约束权限：`allowed_paths`、`blocked_commands`、`may_use_skills`、只读 Reviewer。
5. 回收结果：每个 agent 写 JSON + Markdown result report。
6. 审计交付：Main 跑 gate sync、scope audit，再 final delivery。

| 客户端 | App 完整模式 | CLI 完整模式 | Worker 编排方式 | 备注 |
| --- | --- | --- | --- | --- |
| Codex | ✅ 原生 skill + 原生 subagents | ✅ 原生 skill + subagents / `codex exec` | native subagent 或 `--runtime codex` | Codex App/CLI 都支持 skills；subagents 默认可用 |
| Cursor | ✅ 原生 skill + In-App 子 agent 委派 | ✅ 委派 / 可选 `agent -p` bridge | Main 直接 spawn 子 agent；可选 `--runtime cursor` bridge | App 内首选：Main 直接 spawn Cursor 子 agent 当 Worker（不需外部 CLI）；`agent` CLI bridge 为可选脚本/CI 路径，`/multitask` 为用户驱动备选 |
| Claude Code | ✅ 原生 skill + Claude subagents | ✅ 原生 skill + Claude subagents / `claude --print` | `.claude/agents` 或 `--runtime claude-code` | Claude Code App/IDE 扩展内置 CLI 面板；独立终端自动化需 standalone `claude` |
| OpenClaw / Her | ✅ `sessions_spawn` / `sessions_send` / `sessions_yield` | ✅ runtime 相关 | `--runtime openclaw` / ACP | mission-control 参考实现，其它适配器复用其门控脚本 |
| Hermes | ✅ 原生 `SKILL.md`（agentskills.io 标准）+ 原生 MCP 工具 | ✅ 原生 MCP 工具 + mission-control 脚本 | `--runtime hermes`（打印 MCP / handoff 指引） | 自托管持久 agent；复用 OpenClaw core，`~/.hermes/config.yaml` 注册 MCP coordinator |
| VS Code | scaffold | scaffold | MCP / 任务面板（规划中） | 协议 + 任务面板脚手架，尚未编译发布 |

各端的"完整自动化"都不依赖外部 CLI bridge：Codex / Claude 用原生 subagents，Cursor 用 App 内子 agent 委派（Main 直接 spawn），OpenClaw / Hermes 用原生会话 / MCP 编排。`agent` / `codex` / `claude` 这些 CLI 仅用于可选的脚本/CI bridge。只有当某端既无委派/原生 subagent 能力、又没装对应 CLI 时，才退回 prompt handoff 降级路径。VS Code 目前是脚手架。

## 一键原生安装 / 检查

从解压后的包根目录运行：

```bash
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check
```

`--scope primary` 安装到每个客户端推荐的原生 skill 目录。`--scope all-compatible` 会同时写入兼容目录，例如 `.agents/skills`、`.cursor/skills`、`.claude/skills`、`.codex/skills`。

### 体检（doctor）

`--check` 之外，推荐用更友好的 `doctor`，它会逐客户端检查「skill 是否安装 / 原生 agent 文件是否存在 / App·CLI 是否就位 / 完整 Worker 编排是否就绪」，并给出中文「下一步怎么补齐」：

```bash
python3 scripts/doctor.py            # 全部客户端，友好中文报告
python3 adapters/codex/scripts/doctor_codex.py  # Codex fast path 专项体检
python3 scripts/doctor.py --client cursor
python3 scripts/doctor.py --json     # 机器可读
```

其中 Cursor 在 App 内首选「Main 直接 spawn 子 agent 当 Worker」（不需任何外部 CLI）。只有当你想用**可选的脚本/CI bridge**（`run_multi_agent.py --runtime cursor`）时，才需安装本机 Cursor CLI（命令为 `agent`，旧别名 `cursor-agent` 也可）：

```bash
# macOS / Linux / WSL
curl https://cursor.com/install -fsS | bash
# Windows 原生 PowerShell
irm 'https://cursor.com/install?win32=true' | iex
```

安装后重开终端，`agent --version` 验证；找不到命令时把 `~/.local/bin` 加入 PATH。tmux bridge 还需 `bash` + `tmux`，Windows 原生建议在 WSL 里运行。

`doctor` 覆盖 Codex / Cursor / Claude Code / Hermes 四端（VS Code 仍为脚手架，不在体检范围）。

### 一键注册 MCP（configure_mcp）

把 MCP coordinator 写进各客户端配置，省去手动拼路径。默认 `--dry-run`（只打印将要写入的内容，不落盘），确认后再加 `--write`：

```bash
python3 scripts/configure_mcp.py --client all --workspace .          # 预览（dry-run）
python3 scripts/configure_mcp.py --client cursor --workspace . --write
```

- Cursor / Claude Code 为 JSON 配置，原地合并并保留已有 `mcpServers`（`--write` 才落盘）。
- Codex 为 TOML（`~/.codex/config.toml`），打印可粘贴的 `[mcp_servers.*]` 片段。
- Hermes 为 YAML（`~/.hermes/config.yaml`），打印可粘贴的 `mcp_servers` 片段。

依赖无第三方库（stdlib only）。

## 推荐入口

| 你是谁 | 推荐入口 |
| --- | --- |
| OpenClaw / Her 用户 | [`adapters/openclaw/QUICKSTART.md`](adapters/openclaw/QUICKSTART.md) |
| Cursor App / CLI 用户 | [`adapters/cursor/QUICKSTART.md`](adapters/cursor/QUICKSTART.md) |
| Codex App / CLI 用户 | [`adapters/codex/QUICKSTART.md`](adapters/codex/QUICKSTART.md) |
| Claude Code App / CLI 用户 | [`adapters/claude-code/QUICKSTART.md`](adapters/claude-code/QUICKSTART.md) |
| Hermes Agent 用户 | [`adapters/hermes/QUICKSTART.md`](adapters/hermes/QUICKSTART.md) |
| 想看自动安装入口 | [`docs/agent-install.md`](docs/agent-install.md) |
| 想看 MCP 协议 | [`mcp/multi-agent-coordinator/README.md`](mcp/multi-agent-coordinator/README.md) |
| 想看路线图 | [`docs/roadmap.md`](docs/roadmap.md) |
| 想看最新跑分摘要 | [BENCHMARKS.md](BENCHMARKS.md) |

## 当前能力概览

- **Codex：完整 v0.2**，App/CLI 原生 skill + 原生 subagents，CLI bridge 走 `codex exec`。
- **Cursor：完整 v0.3**，App/CLI 原生 skill；App 内首选「Main 直接 spawn 子 agent 当 Worker」（不需外部 CLI）；`agent` CLI bridge 为可选脚本/CI 路径，`/multitask` 与 headless/`@cursor/sdk` 为备选。
- **Claude Code：完整 v0.2**，App/IDE/CLI 原生 skill + `.claude/agents` subagents，CLI bridge 走 `claude --print`。
- **OpenClaw / Her：Production v1**，作为 mission-control 参考实现。
- **Hermes：适配器已落地**，通过 agentskills.io 标准 `SKILL.md` 被原生发现，借助 Hermes 原生 MCP 客户端（`~/.hermes/config.yaml` 的 `mcp_servers`）复用 OpenClaw mission-control core。
- **原生编排与受控自纠循环：已落地**，Cursor 提供 `/multitask`·`/worktree`·headless·`@cursor/sdk` 原生路径；`run_loop.py` 把 Worker(maker) 与独立 Verifier·审计(checker) 组成有界自纠循环。
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

## Hermes Adapter

[Hermes](https://agentskills.io)（Nous Research，2026）是自托管、always-on 的持久记忆 agent。它加载 agentskills.io 标准的可移植 `SKILL.md`（与本项目同一格式），并内置原生 MCP 客户端，因此装好后会被原生发现。[`adapters/hermes/`](adapters/hermes/) 是一层薄适配，不复制 mission-control 逻辑，而是复用 OpenClaw 的脚本做任务卡、门控、审计与记忆。

| 项 | 说明 |
| --- | --- |
| Native skill | `hermes-multi-agent` |
| 安装目录 | `~/.agents/skills/hermes-multi-agent`、`~/.hermes/skills/hermes-multi-agent` |
| Worker 编排 | Hermes 原生 MCP 工具 + OpenClaw mission-control 脚本 |
| MCP 接入 | `~/.hermes/config.yaml` 的 `mcp_servers`（stdio / http） |

```bash
# 安装原生 skill（也可解压 hermes 包后在包根目录运行）
python3 scripts/install_native_skills.py --client hermes --scope primary --force
# 把 MCP coordinator 注册进 ~/.hermes/config.yaml（打印可粘贴的 yaml 片段）
python3 scripts/configure_mcp.py --client hermes
# 跨端 launcher 会打印 Hermes 的 MCP / handoff 指引
python3 scripts/run_multi_agent.py --runtime hermes --task-card .codex-multi-agent/tasks/T002-worker-backend.md
# 自检
python3 adapters/hermes/scripts/hermes_self_check.py --self-check
```

详见 [`adapters/hermes/QUICKSTART.md`](adapters/hermes/QUICKSTART.md)。

## 跨 Adapter Launcher

所有 client adapter 尽量复用 OpenClaw mission-control core，不复制 gate 逻辑。

```bash
# Codex App full path: build one native spawn plan for all task cards.
python3 scripts/run_multi_agent.py --runtime codex-native-plan --state-dir .codex-multi-agent

# Single-card launch / handoff runtimes.
python3 scripts/run_multi_agent.py --runtime cursor-desktop|cursor|codex-native|codex-desktop|codex|claude-desktop|claude-code|openclaw|hermes --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Launcher 使用 `pipefail` 和 post-run checks：外部 CLI 失败、quota/error pattern、结果 Markdown 过薄、JSON 缺失等都应该返回非零和 `"ok": false`。`--runtime codex-native-plan` 不需要 `--task-card`，它读取 `--state-dir` 下的全部任务卡并生成 Codex App native subagent 分派计划；`--runtime hermes` 不直接拉起进程，而是打印 Hermes 的 MCP / handoff 指引。

## 受控自纠循环（Loop Engineering）

`adapters/openclaw/scripts/run_loop.py` 把 Worker、Verifier 与审计门控升级为一个**有界自纠循环**，而不是放任 agent 无限重试。五要素：Goal（可验证的停止条件）、Actions（maker 每轮做一步）、Verify（**独立** verifier，强制 maker ≠ checker）、Repair（把上轮反馈喂给下一轮 maker）、Memory（逐轮记录），并始终受 `max_iterations` / budget 上界约束。

真实模式里：maker = `run_multi_agent.py` 派发一个 Worker，verifier = `--verify-command`（returncode 0 即通过），可叠加 `--with-audit` 让 `audit_worker_output.py` 的 `ok` 一起作为通过条件。

```bash
# 完全确定性自检（不触碰仓库、不调用任何外部 CLI）
python3 adapters/openclaw/scripts/run_loop.py --self-check
# 真实模式：跑 Worker -> pytest -> 审计，最多 5 轮收敛
python3 adapters/openclaw/scripts/run_loop.py \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --runtime openclaw --verify-command "pytest -q" \
  --with-audit --max-iterations 5 --state-dir .codex-multi-agent
```

## 依赖图：自动解锁与调度（auto-unblock）

`create_task_cards.py` 把静态依赖图写进 `ownership.json` 的每个任务（`dependencies`）；`update_task_status.py --sync` 据此为 `status.json` 每个任务派生 `dependencies` / `blocked_by` / `ready_to_spawn`（**纯增量、不改 gate 通过/失败语义**）。两种消费方式：

```bash
# 查询当前哪些任务可以 spawn、哪些被谁阻塞
python3 adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --ready
# -> {"ready": ["T001"], "blocked": {"T002": ["T001"], ...}}

# 依赖序自动调度整张任务图（默认只输出 dry-plan，--execute 才真正派发 Worker）
python3 adapters/openclaw/scripts/run_graph.py --state-dir .codex-multi-agent
python3 adapters/openclaw/scripts/run_graph.py --state-dir .codex-multi-agent --runtime openclaw --max-rounds 8 --execute
```

`run_graph.py` 反复 `sync → 找就绪任务 → 派发 → 重新评估`，直到全图完成、死锁（有未完成但无就绪任务），或触达 `--max-rounds`（始终有界）。它经 `multi-agent://state` 资源也可被 MCP 客户端读取。

## Tools Layer

`tools/` 下提供 dependency-free stdlib wrappers，供 Worker/Verifier 声明式使用：

| Tool | Purpose |
| --- | --- |
| `git_tool.py` | `git status`、`diff`、changed files |
| `test_runner_tool.py` | 发现并运行 `pytest`、`npm test`、`pnpm test` |
| `lint_tool.py` | best-effort lint / format / type check |
| `shell_tool.py` | allowlist/denylist shell wrapper |
| `repo_index_tool.py` | 文件列表和 grep，`rg` 不可用时 fallback |
| `worktree_tool.py` | 为每个 Worker 创建隔离 git worktree + 分支（可直接对接 `ownership.json`），并行写入互不覆盖 |

每个工具支持 `--help`、JSON-in/JSON-out 和 `--self-check`。

### 并行 Worker 物理隔离（git worktree）

`ownership.allowed_paths` 做的是**逻辑**文件域划分，`audit_worker_output.py` 做的是**事后**越界/冲突检测。`worktree_tool.py` 补上业界（Cursor / Claude Code worktrees）通行的**物理隔离**：每个 Worker 在自己的 git worktree + 分支里写代码，真并行也不会互相覆盖，且天然为「每个 Worker 一个分支 / PR」铺路（roadmap v4）。

```bash
# 直接按 ownership.json 规划：每个 write_permission=true 的 Worker 一个 worktree+分支
python tools/worktree_tool.py --action plan --ownership .codex-multi-agent/ownership.json
# 加 --create 真正创建；Worker 完成后回收：
python tools/worktree_tool.py --action remove --repo-root . --path <worktree_path> --delete-branch
```

默认 worktree 放在 `<repo>.worktrees/` 同级目录，避免污染主工作树的 `git status`（否则会干扰 scope 审计）。

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
- 一键注册到 cursor / claude / codex / hermes：`python3 scripts/configure_mcp.py --client all`（默认 dry-run，`--write` 落盘）
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
v1 scripts：OpenClaw mission-control core + adapters + audit gates（已落地）
v2 MCP：任务、状态、finding、approval、audit 的工具后端（已落地）
v3 IDE panel：任务面板、Prompt 生成器、审计视图（已落地）
v4 tools / memory / bench：stdlib 工具层（含 worktree_tool）、MEMORY、本地 bench（已落地）
v5 SWE-bench Lite 形态 harness、扩展脚手架（已落地，离线为主）
v6 loop engineering（run_loop）、依赖图 auto-unblock + 调度（run_graph / --ready）、Hermes 适配器、Cursor 原生编排（SDK / headless）、doctor / configure_mcp（已落地）
下一步：每 Worker 一分支 → PR review → CI 失败回流（worktree 物理隔离已铺路）
```

详细分层与已落地状态见 [`docs/roadmap.md`](docs/roadmap.md)。
