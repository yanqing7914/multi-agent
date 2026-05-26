# Task R001 — Worker (Cursor runtime)

**Role**: Worker
**Owner runtime**: cursor
**Scenario**: 跨 IDE 接力 demo

## Mission

给 `examples/case-study-flask-cli/` 的 stdlib HTTP server 加一个 `/echo?msg=...` 端点：
- GET `/echo?msg=hello` → `{"echo": "hello"}`
- GET `/echo`（无参数）→ `{"echo": ""}`
- GET `/echo?msg=<empty>` → `{"echo": ""}`
- 不允许调用任何 shell 或第三方 HTTP 库；只用 stdlib（`urllib.parse` OK）

## workspace_root

`/mnt/c/Users/gongchenhao/Documents/Codex/2026-05-18/new-chat-3/multi-agent-coding`

## preflight_command

```bash
cd /mnt/c/Users/gongchenhao/Documents/Codex/2026-05-18/new-chat-3/multi-agent-coding
test -f examples/case-study-flask-cli/app/routes.py
test -f examples/case-study-flask-cli/app/server.py
test -f examples/case-study-flask-cli/tests/test_routes.py
```

## allowed_paths

- `examples/case-study-flask-cli/app/**`
- `examples/case-study-flask-cli/tests/**`

不要碰仓库其他任何文件。

## required_paths（必须读）

- `examples/case-study-flask-cli/app/routes.py`
- `examples/case-study-flask-cli/app/server.py`
- `examples/case-study-flask-cli/tests/test_routes.py`

## acceptance criteria

1. `routes.py` 新增 `echo_payload(msg: str) -> dict` 函数
2. `server.py` 在 `do_GET` 里加 `/echo` 分支，从 query string 解析 `msg`
3. `tests/test_routes.py` 加至少 3 个测试（有 msg / 无 msg / 空 msg）
4. `PYTHONPATH=. pytest examples/case-study-flask-cli/tests -q` 全过
5. 不破坏现有 `test_health_payload` / `test_index_payload_mentions_service` / `test_version_payload` / `test_ping_payload`

## 必须产出（result report）

**JSON**: `.codex-multi-agent-relay/results/R001-worker-echo.json`，schema:
```json
{
  "task_id": "R001-worker-echo",
  "role": "Worker",
  "status": "completed",
  "workspace_observed": "<absolute path>",
  "required_paths_verified": true,
  "required_paths_missing": [],
  "files_read": ["..."],
  "files_changed": ["..."],
  "tools_used": ["pytest", "git", "..."],
  "tests": { "pytest_passed": N, "pytest_failed": 0 },
  "notes": "一段话总结"
}
```

**Markdown**: `.codex-multi-agent-relay/results/R001-worker-echo.md` — 人读版

## Tools / 受控规则

- 不要 commit/push（Main 负责集成）
- 不要碰 `.codex-multi-agent-relay/` 以外的目录的 worker 报告
- 不要修任何 LICENSE / pyproject / CHANGELOG / .github/

## Handoff

完成后输出**单行**："R001-worker-echo: DONE, see .codex-multi-agent-relay/results/R001-worker-echo.{json,md}"，由 Main 接管下一步。
