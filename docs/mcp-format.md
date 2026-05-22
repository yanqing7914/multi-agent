# MCP Format

`multi-agent-coordinator-mcp` is the optional tool backend for this protocol. The skill remains responsible for workflow decisions; MCP stores state and exposes coordination tools.

## Server identity

```json
{
  "name": "multi-agent-coordinator",
  "version": "0.1.0",
  "description": "Task cards, scoped worker coordination, review findings, skill-use approvals, and audit state for multi-agent coding."
}
```

## State directory

```text
.codex-multi-agent/
  state.json
  tasks/
  results/
  findings/
  approvals/
```

The state directory is local-only by default. Do not commit it unless the user explicitly chooses to.

## Core tools

### create_task

Create an Explorer, Worker, Reviewer, or Verifier task card.

Input:

```json
{
  "workspace": "string",
  "task": {
    "id": "string",
    "mode": "research | implement | fix | review | refactor",
    "role": "Explorer | Worker | Reviewer | Verifier",
    "title": "string",
    "objective": "string",
    "context": "string",
    "dependencies": ["string"],
    "allowed_paths": ["string"],
    "forbidden_paths": ["string"],
    "allowed_commands": ["string"],
    "blocked_commands": ["string"],
    "may_use_skills": ["string"],
    "forbidden_skills": ["string"],
    "may_spawn_subagents": false,
    "subagent_budget": 0,
    "validation_required": ["string"],
    "stop_conditions": ["string"]
  }
}
```

Output:

```json
{ "ok": true, "task_id": "T001", "path": ".codex-multi-agent/tasks/T001.json" }
```

### list_tasks

Input:

```json
{ "workspace": "string", "status": "pending | running | completed | blocked | failed | any", "role": "Explorer | Worker | Reviewer | Verifier | any" }
```

### get_task

Input:

```json
{ "workspace": "string", "task_id": "T001" }
```

### update_task_status

Input:

```json
{ "workspace": "string", "task_id": "T001", "status": "pending | running | completed | blocked | failed", "note": "string" }
```

### record_result

Input:

```json
{
  "workspace": "string",
  "result": {
    "task_id": "T001",
    "role": "Explorer | Worker | Reviewer | Verifier",
    "status": "completed | blocked | failed",
    "summary": "string",
    "files_read": ["string"],
    "files_changed": ["string"],
    "validation": [{ "command": "string", "result": "passed | failed | not_run", "notes": "string" }],
    "skills_used": ["string"],
    "risks": ["string"],
    "blockers": ["string"],
    "handoff_notes": "string"
  }
}
```

### check_path_allowed

Input:

```json
{ "workspace": "string", "task_id": "T001", "path": "string", "operation": "read | write" }
```

Output:

```json
{ "allowed": true, "reason": "Path matches allowed_paths." }
```

### record_touched_paths

Input:

```json
{ "workspace": "string", "task_id": "T001", "files_changed": ["string"] }
```

### request_skill_use

Input:

```json
{ "workspace": "string", "task_id": "R001", "requested_skill": "ssrd", "reason": "string", "scope": ["string"], "risk": "string" }
```

### approve_skill_use

Input:

```json
{ "workspace": "string", "request_id": "S001", "approved": true, "approved_scope": ["string"], "expires_after_task": true }
```

### record_finding

Input:

```json
{
  "workspace": "string",
  "finding": {
    "reviewer_task_id": "R001",
    "severity": "P0 | P1 | P2 | P3",
    "title": "string",
    "target_file": "string",
    "line": 1,
    "evidence": "string",
    "recommendation": "string",
    "status": "open | resolved | dismissed"
  }
}
```

### summarize_review

Input:

```json
{ "workspace": "string", "include_resolved": false, "group_duplicates": true }
```

### audit_scope

Input:

```json
{ "workspace": "string" }
```

### generate_final_report

Input:

```json
{ "workspace": "string", "include_tasks": true, "include_findings": true, "include_validation": true }
```

## Resources

Expose these resources when supported by the client:

```text
multi-agent://state
multi-agent://tasks
multi-agent://findings
multi-agent://approvals
```

## Prompts

Recommended prompt templates:

- `create_worker_task_card`
- `create_review_agents_with_ssrd`
- `summarize_multi_agent_results`
- `audit_before_final_delivery`

## Client adapters

The MCP contract should stay stable across Codex, Cursor, Claude Code, OpenClaw, Hermes, and VS Code. Each client adapter is responsible for configuring the MCP server and translating client-specific agent/session features into task cards and result reports.