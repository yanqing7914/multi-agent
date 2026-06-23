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
| `ownership.json` | 路径所有权与 `workspace_root` |
| `audits/` | 范围审计 JSON |
| `findings/` | Reviewer 汇总 |
| `summary/` | `--summarize` 运行摘要 |

详见 [adapters/openclaw/README.md](../adapters/openclaw/README.md)。

## 演进路线（Skill 基线 → v6）

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

**Loop 引擎的位置**：`adapters/openclaw/scripts/run_loop.py` 位于 Adapters / 编排层，把已有的 Worker(maker)、独立 Verifier·`audit_worker_output`(checker)、MEMORY(memory)、门控(stop) 编排成一个有界自纠循环——maker 调 `run_multi_agent.py`，verifier 跑 `--verify-command`（可叠加审计 `ok`），强制 maker ≠ checker，并受 `max_iterations`/budget 上界约束，不改变下层契约。

**Hermes 的位置**：Hermes 是 Adapters 层的一个客户端薄适配，不复制门控逻辑，而是通过其原生 MCP 客户端（`~/.hermes/config.yaml` 的 `mcp_servers`）连到 `mcp/multi-agent-coordinator`，并复用 `adapters/openclaw/scripts/*` 读写同一份 `.codex-multi-agent/` 状态。

## 关键脚本数据流

```text
create_task_cards.py  →  tasks/ + ownership.json + status.json + run-plan.json
        ↓
子 Agent 执行 → results/*.json + *.md
        ↓
update_task_status.py --sync  →  门控 + preflight_issues
        ↓
audit_worker_output.py  →  audits/*.json（ok 仅当 gate.status=passed）
        ↓
update_task_status.py --summarize  →  summary/ + MEMORY.md 追加
```

## 相关文档

- 客户端矩阵：[clients.md](clients.md)
- MCP 工具契约：[mcp-format.md](mcp-format.md)
- 路线图：[roadmap.md](roadmap.md)
- 安全门控注册表：[safety-rules.md](safety-rules.md)
- OpenClaw 适配器：[../adapters/openclaw/README.md](../adapters/openclaw/README.md)
