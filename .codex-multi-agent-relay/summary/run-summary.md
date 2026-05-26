# 跨 IDE 接力 demo · run-summary

**时间**：2026-05-26
**场景**：给 `examples/case-study-flask-cli/` 加一个真实不存在的端点 `/echo?msg=...`

## 接力链路（三家 IDE × 4 个 gate）

| Step | Agent (runtime) | 角色 | 产物 | 状态 |
|------|------------------|------|------|------|
| 1 | OpenClaw Main (主会话) | Mission control | ownership.json / run-plan.json / 2 张 task card | ✅ |
| 2 | Cursor (PTY via tmux) | Worker R001 | echo_payload + /echo 分支 + 3 个测试 (7/7 pytest) | ✅ |
| 3 | Claude Code (ACP) | Reviewer R002 | 5 个 finding (2 P2, 3 P3)，verdict=`approved_with_findings` | ✅ |
| 4 | OpenClaw Main (主会话) | scope_audit + final delivery | audit.ok=true, gate=passed, commit + push | ✅ |

## 为什么这个 demo 重要

之前 codex 和 claude-code 各自跑了同一个 case study 的不同任务，**但没有上下游关系**（codex 跑 `/version` 已存在 → files_changed=[]，claude-code 跑 `/ping` 是另起一炉）。这次是**真正的接力**：

- 同一份 task card 在两个 runtime 间流转
- 同一份 ownership.json 同时约束 Worker 的 allowed_paths 和 Reviewer 的 required_paths
- Reviewer **真读了 Worker 的 result JSON + Markdown**，再独立 rerun pytest
- audit_worker_output 把 reviewer 的 result 也当成 result 审，不仅仅是 worker

**这就是项目目标里"跨 IDE 协作契约"的端到端证据**。

## Reviewer findings 摘要

| ID | 严重度 | 标题 | 建议 |
|----|--------|------|------|
| F1 | P2 | 两个测试功能完全相同 | 用 URL-encoded 或重复参数测试替换 |
| F2 | P2 | server.py 的 query 解析无任何测试覆盖 | 加 HTTPServer 集成测试 |
| F3 | P3 | 重复 ?msg=a&msg=b 静默丢弃后面的值 | 文档化或显式拒绝 |
| F4 | P3 | parse_qs 默认丢空值，模糊了"absent vs empty" | 用 `keep_blank_values=True` |
| F5 | P3 | 新测试命名风格和现有不一致 | 风格统一 |

F1+F2 是有信息量的 review，证明 Claude 真读了代码。

## 防伪 gate 表现

每个产物都经过这些 gate：

- ✅ `required_paths_verified=true`（两个 result 都有）
- ✅ `files_read` 非空（worker 4 个 / reviewer 6 个）
- ✅ `workspace_observed` 等于 ownership 里的 `workspace_root`
- ✅ Worker `files_changed` 全部在 `allowed_paths` 内
- ✅ Reviewer `allowed_paths=[]` 没被违反（没改任何 src）
- ✅ `tools_used` 不为空（worker 4 个 / reviewer 3 个）
- ✅ `scope_audit` gate = passed, violations=[], conflicts=[], warnings=[]

如果任何一项不达标，gate 会拦。这次全过 = 协议设计经得起跨 IDE 实战。

## 文件清单

```
.codex-multi-agent-relay/
├── ownership.json
├── run-plan.json
├── tasks/
│   ├── R001-worker-echo.md
│   └── R002-reviewer-echo.md
├── results/
│   ├── R001-worker-echo.json   (Cursor Worker)
│   ├── R001-worker-echo.md
│   ├── R002-reviewer-echo.json (Claude Reviewer)
│   └── R002-reviewer-echo.md
├── audits/
│   ├── audit-20260526T055323Z.json
│   └── latest.json             (gate=passed, ok=true)
└── summary/
    └── run-summary.md          (本文件)
```

变更的源码（Cursor Worker 写）：
- `examples/case-study-flask-cli/app/routes.py` (+echo_payload)
- `examples/case-study-flask-cli/app/server.py` (+/echo 分支)
- `examples/case-study-flask-cli/tests/test_routes.py` (+3 个测试)
