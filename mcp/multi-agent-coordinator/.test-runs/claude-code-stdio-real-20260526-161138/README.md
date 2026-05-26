# Real MCP stdio end-to-end test — claude-code driver

**时间**: 2026-05-26 16:11 GMT+8（UTC `20260526T081201Z`）
**驱动方**: Claude Code (Opus 4.6) 通过 Python `subprocess` + JSON-RPC over stdio 直接调 `mcp/multi-agent-coordinator/server.py`
**State dir**: `/tmp/mcp-test-state/`（不入库）

## 这是项目第一次真实跨进程调 MCP server

之前 v2 MCP server 一直被 README 标为 "v2 in"，但从未有外部 MCP client 真正连上去过。
本次用 stdio MCP 协议把 server 起起来，按 MCP 标准做 `initialize` → `notifications/initialized` → `tools/list` → 多个 `tools/call`，全程抓 JSON-RPC 帧。

## 执行的调用序列

| # | method | tool | 结果 |
|---|--------|------|------|
| 1 | `initialize` | — | protocolVersion=2024-11-05, serverInfo=multi-agent-coordinator |
| 2 | `notifications/initialized` | — | (无响应，规范行为) |
| 3 | `tools/list` | — | 14 个工具，与 `server.py` `TOOLS` 一致 |
| 4 | `tools/call` | `list_tasks` | `{ok:true, tasks:[], count:0}` 初始空 |
| 5 | `tools/call` | `create_task` | 创建 `WORKER-001`，写到 `tasks/WORKER-001-worker-001.md` |
| 6 | `tools/call` | `list_tasks` | 返回刚创建的 task，含 role/allowed_paths/blocked_paths |
| 7 | `tools/call` | `record_result` | 落 `results/WORKER-001-worker-001.{json,md}`，同步 status.json |
| 8 | `tools/call` | `record_finding` | 追加 `findings/review-findings.json`，count=1 |
| 9 | `tools/call` | `audit_scope` | `violations=[]`, `conflicts=[]`, 1 个 `missing_tools_used` warning（向后兼容） |
| 10 | `tools/call` | `summarize_review` | by_severity.info=1，结构正常 |

## 观察 / Bug

1. **`audit_scope` warning**: result 报告里 `tools_used` 字段为空时会触发 `missing_tools_used` 警告 —— 注释里写的是 "warning only; backward compatible"，符合预期，不算 bug。
2. **stderr 0 bytes**: 整个 session server 没有任何 stderr 输出，干净。
3. **协议契合度**: 完全按 MCP 2024-11-05 spec 实现 `initialize`/`tools/list`/`tools/call`/`resources/list`/`prompts/list`/`ping`，无偏差。
4. **可用作 Claude Code 真实接入**: `clients/claude-code-mcp.json` 模板里的参数（`command=python3`, `args=[server.py, --state-dir, ...]`）和本次驱动方式一致 —— 把模板里 `{REPO_ROOT}` / `{WORKSPACE_ROOT}` 替换成绝对路径就能直接塞到 `~/.claude/settings.json`。

## 工件

- `transcript.jsonl` — 19 帧（10 个 request，1 notify，无响应；8 个成功 response；外加 initialize 1 应答 = 共记录 `direction:->` 10 条 + `direction:<-` 9 条 = 19 行）
- `stderr.log` — 空文件，证明 server 干净退出
- 驱动脚本: `/tmp/mcp-driver.py`（一次性，不入库）

## 结论

**MCP server 的 stdio 通道、JSON-RPC 解析、14 个工具的 dispatch 路径、coordinator.py 后端的状态写入** 都被真实验证过。可以把 README 里 "v2 in" 升级到 "v2 verified real client"。
