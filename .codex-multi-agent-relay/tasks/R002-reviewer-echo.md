# Task R002 — Reviewer (Claude Code via ACP)

**Role**: Reviewer
**Owner runtime**: claude-code (via ACP)
**Scenario**: 跨 IDE 接力 demo —— 评审 Cursor Worker 的 /echo 实现

## Mission

Cursor Worker（R001）已完成 `/echo` 端点。你的工作是**只读评审**——不能改任何代码。

读 worker 的产物（results JSON + 实际修改的代码），从以下维度评审：

1. **契约一致性**：实现是否真的符合 R001 acceptance criteria？
2. **安全性**：`msg` 参数是否做了 URL decode？有没有 reflected XSS 风险（虽然返回 JSON 但 Content-Type 是否正确）？是否对 binary / 极长 msg 做了边界考虑？
3. **测试覆盖**：3 个测试是否包括边界 case（无 msg / 空 msg / 含特殊字符 msg / 含 URL-encoded msg / 极长 msg）？
4. **代码风格**：和现有 routes.py 风格一致？
5. **可回归**：worker 是否破坏了任何现有测试？

## workspace_root

`/mnt/c/Users/gongchenhao/Documents/Codex/2026-05-18/new-chat-3/multi-agent-coding`

## preflight_command

```bash
cd /mnt/c/Users/gongchenhao/Documents/Codex/2026-05-18/new-chat-3/multi-agent-coding
test -f .codex-multi-agent-relay/results/R001-worker-echo.json
test -f .codex-multi-agent-relay/results/R001-worker-echo.md
test -f examples/case-study-flask-cli/app/routes.py
PYTHONPATH=examples/case-study-flask-cli pytest examples/case-study-flask-cli/tests -q
```

## allowed_paths

**空**——Reviewer 是只读角色。

## required_paths（必须读）

- `examples/case-study-flask-cli/app/routes.py`
- `examples/case-study-flask-cli/app/server.py`
- `examples/case-study-flask-cli/tests/test_routes.py`
- `.codex-multi-agent-relay/results/R001-worker-echo.json`
- `.codex-multi-agent-relay/results/R001-worker-echo.md`

## acceptance criteria

1. 必须**逐条** assert R001 acceptance criteria 是否满足
2. 必须发现 **at least 1 个 finding**（即使是 P3 / informational），demonstrate reviewer 真读过代码
3. 必须 **rerun pytest** 并记录结果
4. 不能改任何 src 或 test 文件

## 必须产出

**JSON**: `.codex-multi-agent-relay/results/R002-reviewer-echo.json`:
```json
{
  "task_id": "R002-reviewer-echo",
  "role": "Reviewer",
  "status": "completed",
  "workspace_observed": "<absolute path>",
  "required_paths_verified": true,
  "required_paths_missing": [],
  "files_read": ["..."],
  "tools_used": ["pytest", "..."],
  "acceptance_check": {
    "criterion_1_echo_payload_exists": "pass|fail",
    "criterion_2_server_echo_branch": "pass|fail",
    "criterion_3_three_tests": "pass|fail",
    "criterion_4_pytest_passes": "pass|fail",
    "criterion_5_no_regression": "pass|fail"
  },
  "findings": [
    {"id": "F1", "severity": "P1|P2|P3", "title": "...", "evidence": "file:line"}
  ],
  "pytest_rerun": { "passed": N, "failed": 0 },
  "verdict": "approved|approved_with_findings|rejected",
  "notes": "..."
}
```

**Markdown**: `.codex-multi-agent-relay/results/R002-reviewer-echo.md` — 人读版

## Handoff

完成后输出**单行**："R002-reviewer-echo: DONE, verdict=<approved|approved_with_findings|rejected>"，由 Main 接管 audit + final delivery。
