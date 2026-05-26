# multi-agent-coordinator MCP Server (v2)

Dependency-free MCP server that maps the v1 `.codex-multi-agent/` state schema into MCP tools, resources, and prompts. The skill remains responsible for workflow decisions; this server stores state and exposes coordination tools.

## Install

No dependencies. Python 3.11+ standard library only.

```bash
# From any workspace
python3 /path/to/multi-agent-coding/mcp/multi-agent-coordinator/server.py --state-dir .codex-multi-agent
```

Optional env:

- `WORKSPACE` — if set and `--state-dir` omitted, uses `$WORKSPACE/.codex-multi-agent`

## Register with clients

Per-client snippets (copy-paste JSON):

- [Cursor](clients/cursor.md)
- [Claude Code](clients/claude.md)
- [Codex](clients/codex.md)
- [OpenClaw / ACP](clients/openclaw.md)

### Cursor (summary)

Add to `.cursor/mcp.json` (or Cursor MCP settings):

```json
{
  "mcpServers": {
    "multi-agent-coordinator": {
      "command": "python3",
      "args": [
        "/absolute/path/to/multi-agent-coding/mcp/multi-agent-coordinator/server.py",
        "--state-dir",
        "/absolute/path/to/your/workspace/.codex-multi-agent"
      ]
    }
  }
}
```

### Claude Code

```json
{
  "mcpServers": {
    "multi-agent-coordinator": {
      "command": "python3",
      "args": [
        "/absolute/path/to/multi-agent-coding/mcp/multi-agent-coordinator/server.py",
        "--state-dir",
        ".codex-multi-agent"
      ],
      "cwd": "/absolute/path/to/your/workspace"
    }
  }
}
```

### Codex

Configure the MCP server in your Codex MCP settings using the same `command` / `args` shape as above.

## Tools (v1 surface)

| Tool | Backing |
| --- | --- |
| `create_task` | `create_task_cards.py` (`write_card`, status/plan init) |
| `list_tasks` / `get_task` | `ownership.json`, `tasks/` |
| `update_task_status` | `update_task_status.py` |
| `record_result` | `results/` + sync |
| `check_path_allowed` | `audit_worker_output.matches` |
| `record_touched_paths` | result JSON merge |
| `request_skill_use` / `approve_skill_use` | `approvals/` |
| `record_finding` / `summarize_review` | `findings/` + sync |
| `audit_scope` | `audit_worker_output.py --write-audit` |
| `generate_final_report` | `update_task_status.py --summarize` |

## Resources

| URI | File |
| --- | --- |
| `multi-agent://state` | `status.json` |
| `multi-agent://tasks` | `tasks/` listing |
| `multi-agent://findings` | `findings/review-findings.json` |
| `multi-agent://approvals` | `approvals/` listing |

## Prompts

- `create_worker_task_card`
- `create_review_agents_with_ssrd`
- `summarize_multi_agent_results`
- `audit_before_final_delivery`

## Security

- **Scope:** Read/write is limited to the configured `--state-dir` (typically `.codex-multi-agent/` under your workspace).
- **No network:** The server does not open ports or call external APIs.
- **Not a sandbox:** Path checks are advisory; they mirror v1 script helpers and do not enforce OS-level isolation.

## Known limitations (v1)

- Single-task `create_task` adds to existing state; bulk YAML generation still uses `create_task_cards.py` directly.
- MCP does not spawn agents; clients must launch Explorer/Worker/Reviewer/Verifier sessions.
- `check_path_allowed` uses glob rules from ownership, not live filesystem ACLs.
- Protocol surface is minimal (initialize, tools, resources, prompts) — no sampling or logging handlers.

## Self-check

```bash
python3 mcp/multi-agent-coordinator/scripts/self_check.py
```

## 客户端接入

Copy-paste JSON snippets (replace placeholders, then merge into your IDE MCP config):

| Client | Snippet file |
| --- | --- |
| Claude Code (`~/.config/claude/mcp.json` or desktop config) | [`clients/claude-code-mcp.json`](clients/claude-code-mcp.json) |
| Cursor (`~/.cursor/mcp.json` or **Settings → MCP**) | [`clients/cursor-mcp.json`](clients/cursor-mcp.json) |
| Codex CLI / Gemini-style stdio MCP | [`clients/codex-mcp.json`](clients/codex-mcp.json) |

**Placeholders**

- `{REPO_ROOT}` — absolute path to this `multi-agent-coding` checkout
- `{WORKSPACE_ROOT}` — absolute path to the project you are dogfooding (where `.codex-multi-agent/` lives)

**Smoke test (no IDE required)**

```bash
export REPO_ROOT="$(pwd)"
export WORKSPACE_ROOT="$(pwd)"
python3 mcp/multi-agent-coordinator/scripts/self_check.py
```

**Smoke test (Cursor / any MCP client)**

1. Paste `clients/cursor-mcp.json` into `.cursor/mcp.json` with real paths.
2. Restart Cursor MCP (or reload window).
3. Invoke tool `list_tasks` with `{}` or `{"workspace": "<your workspace>"}`.
4. Expect JSON listing tasks from `ownership.json` (empty list if state dir is fresh).

Local agent verification in this batch used `self_check.py` only (IDE MCP attach not available in CI/WSL headless). The stdio server responds to `tools/list` and `tools/call` for `list_tasks` per `scripts/self_check.py`.

See also [`docs/mcp-format.md`](../../docs/mcp-format.md) and [`docs/roadmap.md`](../../docs/roadmap.md).

## Real MCP transcript

项目第一次真实跨进程调 MCP server 的端到端证据（stdio + JSON-RPC，按 MCP 2024-11-05 spec）：

- [`.test-runs/claude-code-stdio-real-20260526-161138/`](.test-runs/claude-code-stdio-real-20260526-161138/)
  - `transcript.jsonl` — 19 帧 JSON-RPC（initialize / tools/list / list_tasks ×2 / create_task / record_result / record_finding / audit_scope / summarize_review）
  - `README.md` — 中文说明：执行序列、观察、bug 记录
- 驱动方：Claude Code (Opus 4.6) 通过 Python `subprocess` stdio 调用 `server.py`
- 结果：14 个工具全部 dispatch 成功，server stderr 干净，无崩溃
