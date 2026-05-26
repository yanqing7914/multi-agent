# 安全门控注册表

OpenClaw v1 在 `adapters/openclaw/scripts/` 中实现的**反虚假完成**与范围规则。按严重度从高到低排序。

| 严重度 | 规则 ID | 动作 |
| --- | --- | --- |
| **block** | `false_completion` | 任务 `blocked`；门控失败 |
| **block** | `workspace_mismatch` | 任务 `blocked`；审计 violation |
| **block** | `thin_evidence` | 任务 `blocked`；审计 violation |
| **block** | `missing_result_report_json` | 任务 `blocked`；门控失败 |
| **block** | `invalid_status_token` | 任务 `blocked`；门控失败 |
| **block** | 范围/秘密路径违规 | 审计 `gate.status=failed`；`ok=false` |
| **pending** | `stale_audit` | `scope_audit` 保持 pending；`latest_audit.ok=false` |
| **warn** | `missing_tools_used` | 审计 warning；不单独失败门控 |
| **warn** | `undeclared_tool_used` | 审计 warning |
| **exempt** | `mission_control_exempt` | 忽略 Worker 对 `.codex-multi-agent/**` 的变更计数 |

---

## false_completion

| 项 | 内容 |
| --- | --- |
| **检查** | `status=completed` 但 `required_paths_verified=false` 或 `required_paths_missing` 非空 |
| **实现** | `_preflight.py:78-93` `false_completion_reason()`；`effective_status_issues()` 合并元数据 |
| **同步** | `update_task_status.py:142-144` 调用 `effective_status_issues`；任务状态降为 `blocked` |
| **审计** | `audit_worker_output.py:280-299` 有 false_reason 时记 violation，跳过路径检查 |
| **动作** | **block** |

---

## workspace_mismatch

| 项 | 内容 |
| --- | --- |
| **检查** | `workspace_observed` 解析后与 `ownership.workspace_root` 不一致 |
| **实现** | `_preflight.py:15-28` `workspace_mismatch_reason()` |
| **同步** | `update_task_status.py` 经 `effective_status_from_result` → `effective_status_issues` |
| **审计** | `audit_worker_output.py:278-290` mismatch 时 violation |
| **动作** | **block** |

---

## thin_evidence

| 项 | 内容 |
| --- | --- |
| **检查** | Explorer/Reviewer/Verifier 在 `required_paths_verified=true` 且存在具体 `required_paths` 时 `files_read` 为空 |
| **实现** | `_preflight.py:96-125` `thin_evidence_reason()` |
| **同步** | `update_task_status.py` `preflight_issues` 含 `thin_evidence: true` |
| **审计** | `audit_worker_output.py:281-308` thin_reason 时 violation |
| **动作** | **block** |

---

## missing_result_report_json

| 项 | 内容 |
| --- | --- |
| **检查** | 角色任务标记 `completed` 但缺少 JSON 结果；仅 Markdown 亦视为不足 |
| **实现** | `_preflight.py:171-191` `missing_result_report_reason()` |
| **同步** | `update_task_status.py:410-420` 强制 `blocked` + `missing_result_report: true` |
| **动作** | **block** |

---

## invalid_status_token

| 项 | 内容 |
| --- | --- |
| **检查** | 结果报告中 `status` 不在 `pending|running|completed|blocked|failed` |
| **实现** | `update_task_status.py:131-140` `effective_status_from_result()` |
| **动作** | **block**（视为虚假完成类问题） |

---

## stale_audit

| 项 | 内容 |
| --- | --- |
| **检查** | `changed-files.txt` 摘要/mtime 与最新 `audits/*.json` 中 `changed_files_digest` 不一致，或文件晚于审计生成 |
| **实现** | `_preflight.py:231-267` `audit_stale_reason()` |
| **同步** | `update_task_status.py:261-290` `resolve_scope_audit()` → `gate_status=pending`, `ok=false`, `stale=true` |
| **动作** | **pending**（须重新 `git diff` + `audit_worker_output.py --write-audit`） |

---

## mission_control_exempt

| 项 | 内容 |
| --- | --- |
| **检查** | Worker `files_changed` 是否计入 `.codex-multi-agent/**` 或 `state_dir` 下路径 |
| **实现** | `audit_worker_output.py:46-56` `mission_control_exempt()`；应用处 `:339-340` |
| **动作** | **exempt**（不计入越界/所有权冲突） |

---

## missing_tools_used

| 项 | 内容 |
| --- | --- |
| **检查** | 结果报告 `tools_used` 为空 |
| **实现** | `audit_worker_output.py:219-226` `tools_used_warnings()` |
| **动作** | **warn**（`gate_warnings` 计算时排除，不单独导致 pending） |

---

## undeclared_tool_used

| 项 | 内容 |
| --- | --- |
| **检查** | 结果中 `tools_used` 含任务卡未声明的工具名 |
| **实现** | `audit_worker_output.py:228-240` |
| **动作** | **warn** |

---

## 审计 ok 语义（scope_audit）

| 项 | 内容 |
| --- | --- |
| **检查** | `audit_worker_output.py` 仅在无 violation/conflict 且无未解决 gate_warning 时 `gate.status=passed` |
| **实现** | `audit_worker_output.py:392-400` — `ok = (audit_gate_status == "passed")` |
| **同步** | `update_task_status.py:278-294` stale 或 failed 时 `latest_audit.ok=false` |
| **动作** | 未通过 → **pending** 或 **failed**；退出码 `2`（pending） |

---

## 仓库级约定

- [AGENTS.md](../AGENTS.md) — 角色与必填结果字段
- [checklists/safety.md](../checklists/safety.md) — 敏感路径与禁止命令（prompt 层，非脚本强制）

维护时新增门控请同步更新本表与 `validate_all.py` / 各脚本 `--self-check`。
