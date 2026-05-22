# multi-agent

面向 Codex、Cursor、Claude Code、OpenClaw、Hermes、VS Code 的多 Agent 协作协议、Skill 与 MCP 设计。

本仓库当前包含第一版 `multi-agent-coding` Skill，以及后续 MCP/IDE 插件的接口规格文档。它的目标不是做一个失控的 agent swarm，而是让多个 agent 在复杂工程任务中按“任务卡、权限边界、评审、验证、最终集成”的方式协作。

## 项目定位

```text
Skill = 协作方法论和提示词规约
MCP = 任务、状态、审批、评审和审计的工具后端
IDE Plugin = 图形化任务面板、Prompt 生成器和本地集成入口
```

当前已实现的是 Skill 和文档规格；MCP Server 与 IDE 插件属于后续实现方向。

## multi-agent-coding Skill

`multi-agent-coding` 是一个 prompt-guided 的多 Agent 编码协作 Skill，用于指导 agent 在复杂代码任务中完成：

```text
需求理解 → 环境检查 → 任务拆解 → 并行调研 → 受控实现 → Diff 审计 → 多视角评审 → 验证 → 最终交付
```

核心角色：

- `Main Agent`：主控，负责规划、分派、集成、验证和最终交付。
- `Explorer`：只读调研代码、架构、测试、约定和风险。
- `Worker`：在 `allowed_paths` 内受控实现，不得越权。
- `Reviewer`：只读评审，不改代码，可使用 `ssrd` 等评审 Skill。
- `Verifier`：运行或描述测试、构建、lint、复现步骤。
- `Integrator`：通常由 Main Agent 扮演，负责合并和最终一致性。

## 能解决什么问题

- 复杂任务拆不清，容易边做边猜。
- 大型代码库上下文太大，需要多个 Explorer 并行调研。
- 前后端、后端、测试、文档等任务可以分工，但容易互相覆盖。
- Worker 使用其他 Skill 时缺少授权边界。
- 多个 reviewer 的意见需要去重、排序和汇总。
- 最终交付前缺少 Diff 审计和验证闭环。

## 重要说明

这个 Skill 是协作规约，不是安全沙箱，也不是自动编排器。它不能真正强制隔离文件系统、网络、Git 或进程权限。

它提供的是：

- 什么时候应该使用多 Agent。
- 如何写任务卡。
- Worker 能改哪些路径。
- Worker 什么时候可以使用其他 Skill。
- Reviewer 如何只读评审。
- Main Agent 如何审计 Diff 和汇总结果。

真正的状态管理、权限检查、任务面板和审计工具，建议通过后续 MCP Server 和 IDE 插件实现。

## 目录结构

```text
SKILL.md                         # Codex/OpenClaw 风格 Skill 主文件
agents/openai.yaml               # Codex UI 元数据
templates/task-card.md           # 子任务卡模板
templates/result-report.md       # 子 Agent 结果报告模板
templates/final-delivery.md      # 最终交付模板
checklists/                      # 启用多 Agent、环境、权限、安全、Diff 审计检查清单
examples/                        # feature / bugfix / review 示例流程
docs/clients.md                  # Codex/Cursor/Claude/OpenClaw/Hermes/VS Code 支持模型
docs/mcp-format.md               # MCP 工具、资源、Prompt 格式规格
```

## 触发条件

适合触发 `multi-agent-coding` 的情况：

- 用户明确说“用多个 agent”“开 subagent”“并行处理”“多个 reviewer 评审”。
- 任务涉及多个独立模块或技术层，例如前端、后端、数据库、测试。
- 需要先调研再实现，再评审和验证。
- 代码库较大，单 agent 上下文压力高。
- 用户要求多视角评审、安全审查、架构审查、复杂 bug 定位。
- Worker 需要使用其他 Skill，但必须有权限边界。

不建议触发的情况：

- 单文件小改动。
- 明确的小 bug。
- 简单解释代码。
- 改文案、改配置字段等轻量任务。
- 没有安全的任务拆分边界。

## Quick Path 与 Multi-Agent Path

小任务走 Quick Path：

```text
Intake → Plan Lite → Implement/Answer → Review Lite → Verify → Deliver
```

复杂任务走 Multi-Agent Path：

```text
Intake → Environment Check → Task Graph → Explorer Fan-out → Synthesis → Scoped Worker → Diff Audit → Reviewer → Verifier → Deliver
```

## Worker 使用其他 Skill 的规则

Worker 可以使用其他 Skill，但不能借 Skill 越权。

Worker 使用 Skill 必须满足：

- Skill 在任务卡的 `may_use_skills` 中，或 Main Agent 明确批准。
- Skill 与当前 Worker 目标直接相关。
- 不扩大 `allowed_paths`。
- 不运行 `blocked_commands`。
- 不访问 secret、token、cookie、SSH key、云凭据等敏感文件。
- 不改变 Worker 的角色，例如从实现者变成部署者或 Git 操作者。

如果不满足条件，Worker 必须停止并提交 `Skill Use Request`。

示例：多个 agent 使用 `ssrd` 评审方案时，应创建多个只读 `Reviewer`，而不是写权限 Worker：

```yaml
mode: review
role: Reviewer
may_use_skills:
  - ssrd
write_permission: false
may_spawn_subagents: false
```

## 跨客户端支持

本仓库目标支持：

- Codex
- Cursor
- Claude Code
- OpenClaw
- Hermes
- VS Code

不同客户端的 agent 启动方式、插件机制、MCP 配置不同，但共享的协议应该保持一致：

- Task Card
- Result Report
- Role Permission
- Skill Use Approval
- Review Finding
- Scope Audit
- Final Delivery

详细设计见：

- `docs/clients.md`
- `docs/mcp-format.md`

## MCP 设计方向

后续可以实现一个 `multi-agent-coordinator-mcp`，用于提供：

- `create_task`
- `list_tasks`
- `get_task`
- `update_task_status`
- `record_result`
- `check_path_allowed`
- `record_touched_paths`
- `request_skill_use`
- `approve_skill_use`
- `record_finding`
- `summarize_review`
- `audit_scope`
- `generate_final_report`

MCP 负责状态和工具化操作，Skill 负责协作流程和行为边界。

## IDE 插件方向

后续可以支持 VS Code / Cursor 插件，提供：

- Task Board：查看 pending/running/blocked/completed 任务。
- Create Task：图形化创建 Explorer/Worker/Reviewer/Verifier 任务卡。
- Findings View：展示 reviewer findings，并支持跳转文件行号。
- Skill Approval Center：管理 Worker/Reviewer 使用其他 Skill 的审批。
- Scope Audit：一键检查 Worker 是否越界、是否有冲突。
- Prompt Generator：为 Codex、Cursor、Claude Code、OpenClaw、Hermes 生成适配 prompt。
- Final Report：一键生成最终交付摘要。

## 使用方式

将本目录复制到 Codex Skill 目录，或作为项目内 Skill 使用，然后显式调用：

```text
Use $multi-agent-coding to coordinate this coding task with scoped roles, review, and verification.
```

中文示例：

```text
使用 $multi-agent-coding，把这个功能拆成 Explorer、Worker、Reviewer 和 Verifier 来做。
```

```text
使用 $multi-agent-coding，开多个 Reviewer，并让它们用 ssrd 评审这个方案。
```

```text
使用 $multi-agent-coding，判断这个任务是否值得开多个 agent；如果不值得，就走 Quick Path。
```

## 当前状态

- 已完成：`multi-agent-coding` Skill v0.1。
- 已完成：任务卡、结果报告、最终交付模板。
- 已完成：环境、权限、安全、Diff 审计检查清单。
- 已完成：Codex/Cursor/Claude Code/OpenClaw/Hermes/VS Code 支持模型文档。
- 已完成：MCP 格式文档。
- 待实现：MCP Server。
- 待实现：VS Code / Cursor IDE 插件。

## 路线图

```text
v0.1 Skill：协作流程、任务卡、权限边界、评审和验证模板
v0.2 MCP Server：任务状态、审批、finding、scope audit、final report
v0.3 VS Code / Cursor Plugin：任务面板、Prompt 生成器、审计视图
v0.4 Client Adapters：Claude Code、OpenClaw、Hermes 适配
v0.5 Worktree / PR / CI：并行分支、PR review、CI 失败回流
```
