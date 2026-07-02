# 架构概览

multi-agent-coding 将**协作协议**（Skill）、**状态工具**（MCP/脚本）、**IDE 呈现**与**客户端运行时**分层解耦，避免「失控 agent swarm」。

## 分层模型（当前）

```text
┌─────────────────────────────────────────────────────────────────┐
│  Skill（prompt）                                                 │
│  SKILL.md / adapters/*/SKILL.md — 流程、角色、权限、交付格式      │
└────────────────────────────┬────────────────────────────────────┘
                             │ 任务卡 / 结果报告契约
┌────────────────────────────▼────────────────────────────────────┐
│  MCP Server（可选）                                              │
│  mcp/multi-agent-coordinator/ — 任务、门控、审计、finding 工具    │
└────────────────────────────┬────────────────────────────────────┘
                             │ 读写 .codex-multi-agent/
┌────────────────────────────▼────────────────────────────────────┐
│  IDE Plugin / 任务面板（可选）                                    │
│  ide/multi-agent-panel/ — 本地 Web UI、VS Code/Cursor 脚手架      │
└────────────────────────────┬────────────────────────────────────┘
                             │ 生成/展示任务卡、状态
┌────────────────────────────▼────────────────────────────────────┐
│  Adapters（客户端薄层）                                           │
│  openclaw · cursor · codex · claude-code · hermes                 │
│  复用 adapters/openclaw/scripts/* 门控逻辑                        │
│  run_loop.py = 有界自纠循环（maker≠checker）                      │
└────────────────────────────┬────────────────────────────────────┘
                             │ sessions_spawn / codex / agent / claude / MCP
┌────────────────────────────▼────────────────────────────────────┐
│  Runtimes（外部 Agent 执行环境）                                  │
│  Codex · Claude Code · Cursor Agent · OpenClaw native/ACP ·       │
│  Hermes（原生 MCP 客户端）· Gemini*                               │
└─────────────────────────────────────────────────────────────────┘
  * Gemini 等未单独适配时，可沿用协议 + MCP，由用户自备运行时。
```

## 本地状态（v1 Mission Control）

无 MCP 时，OpenClaw 脚本直接读写目标仓库下的 `.codex-multi-agent/`：

| 路径 | 用途 |
| --- | --- |
| `tasks/` | 任务卡 Markdown |
| `results/` | 子 Agent JSON + Markdown 结果 |
| `status.json` | 门控与任务状态（`update_task_status.py --sync`） |
| `ownership.json` | 路径所有权与 `workspace_root`；启用 worktree 隔离时同步记录每个 Worker 的 worktree 分支与路径 |
| `worktree-plan.json` | ≥2 个有写权限 Worker 时由 `create_task_cards.py` 生成，每个 Worker 一个隔离 worktree + 分支 |
| `changed-files.txt` | `capture_changed_files.py` 写入：staged + unstaged + untracked 的并集，自动排除 state 目录 |
| `.state.lock` | `_locking.py` 建议锁文件，保护状态目录的并发写入 |
| `audits/` | 范围审计 JSON |
| `findings/` | Reviewer 汇总 |
| `summary/` | `--summarize` 运行摘要 |

**并发安全**：多个 `update_task_status.py` 进程并发更新 `ownership.json` / `status.json` 曾是整文档的 read-modify-write，后写者会静默丢弃先写者的更新。该竞态由 `adapters/openclaw/scripts/_locking.py` 解决——msvcrt/fcntl 跨平台建议锁 + 临时文件原子替换写入；`update_task_status.py` 的所有 CLI 变更入口与 `audit_worker_output.py --write-audit` 均在 state 目录锁内执行，读者不会再读到半截文件。

详见 [adapters/openclaw/README.md](../adapters/openclaw/README.md)。

## 演进路线（Skill 基线 → v7）

与 [roadmap.md](roadmap.md)、根 [README.md](../README.md) 一致：

| 版本 | 焦点 | 状态 |
| --- | --- | --- |
| **Skill 基线** | Skill：任务卡、权限、评审/验证模板 | ✅ 已落地 |
| **v1** | Prompt + 脚本 + `.codex-multi-agent/` | ✅ OpenClaw 参考实现 |
| **v2** | MCP 状态服务 `multi-agent-coordinator` | ✅ 已落地 |
| **v3** | IDE 任务面板 `ide/multi-agent-panel` | ✅ 已落地 |
| **v4** | 工具层（含 `worktree_tool`）、MEMORY、本地 bench | ✅ 已落地 |
| **v5** | SWE-bench Lite 形态 harness、扩展脚手架 | ✅ 已落地（离线为主） |
| **v6** | 自纠循环 `run_loop`、Hermes 适配器、Cursor 原生编排（SDK/headless）、`doctor`/`configure_mcp` | ✅ 已落地 |
| **v7** | 生产加固：默认 worktree 编排、`_locking` 状态锁、`capture_changed_files` 审计输入、`multi-agent-coding` pip CLI | ✅ 已落地 |

**Loop 引擎的位置**：`adapters/openclaw/scripts/run_loop.py` 位于 Adapters / 编排层，把已有的 Worker(maker)、独立 Verifier·`audit_worker_output`(checker)、MEMORY(memory)、门控(stop) 编排成一个有界自纠循环——maker 调 `run_multi_agent.py`，verifier 跑 `--verify-command`（可叠加审计 `ok`），强制 maker ≠ checker，并受 `max_iterations`/budget 上界约束，不改变下层契约。

**Hermes 的位置**：Hermes 是 Adapters 层的一个客户端薄适配，不复制门控逻辑，而是通过其原生 MCP 客户端（`~/.hermes/config.yaml` 的 `mcp_servers`）连到 `mcp/multi-agent-coordinator`，并复用 `adapters/openclaw/scripts/*` 读写同一份 `.codex-multi-agent/` 状态。

## 并行 Worker 隔离（默认）

`create_task_cards.py --worktrees auto|always|off` 控制 git worktree 物理隔离，`auto` 为默认值：检测到 2 个及以上有写权限的 Worker 时自动生成 `worktree-plan.json`，每张 Worker 卡带 `worktree:` 块（分支、路径、create/capture/merge/remove 完整命令），Worker 在各自的隔离 worktree + `multi-agent/<task>-<session>` 分支内工作，互不覆写。单 Worker 无并行覆写风险时自动跳过；`off` 可显式关闭，`always` 强制开启。

## 分发与安装

除源码 checkout 外，提供 pip 包 `multi_agent_coding` 与 `multi-agent-coding` 控制台命令：子命令 `doctor / install / cards / status / capture / audit / worktree / run` 一一转发到打包脚本，`self-check` 与 `path` 用于验证与定位安装。hatchling 构建通过 `force-include` 把整棵技能树打进 wheel 的 `_bundle/`（仓库内仍是单一事实来源），两种形态都能解析技能树。发布走 `release-pypi.yml`（tag 触发，PyPI Trusted Publishing，含 tag/版本一致性检查与 wheel 冒烟测试）。

## 关键脚本数据流

```text
create_task_cards.py  →  tasks/ + ownership.json + status.json + run-plan.json
                          [+ worktree-plan.json，当 ≥2 个有写权限 Worker]
        ↓
Main 按卡片 create 各 Worker worktree（tools/worktree_tool.py）
        ↓
Worker 在各自 worktree 内编辑 → results/*.json + *.md
        ↓
capture_changed_files.py  →  changed-files.txt（staged+unstaged+untracked）
        ↓
update_task_status.py --sync  →  门控 + preflight_issues（state_lock 内）
        ↓
audit_worker_output.py --write-audit  →  audits/*.json（state_lock 内，
                                          ok 仅当 gate.status=passed）
        ↓
审计通过后 git merge --no-ff multi-agent/* 分支，并 remove worktree
        ↓
update_task_status.py --summarize  →  summary/ + MEMORY.md 追加
```

## 相关文档

- 客户端矩阵：[clients.md](clients.md)
- MCP 工具契约：[mcp-format.md](mcp-format.md)
- 路线图：[roadmap.md](roadmap.md)
- 安全门控注册表：[safety-rules.md](safety-rules.md)
- OpenClaw 适配器：[../adapters/openclaw/README.md](../adapters/openclaw/README.md)
