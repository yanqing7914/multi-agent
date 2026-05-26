# Hermes adapter scaffold (future)

Hermes is documented in [`docs/clients.md`](../../../docs/clients.md) as a planned client. This folder describes how a future Hermes adapter would integrate — **no runnable code yet**.

## Planned responsibilities

| Layer | Hermes adapter would… |
| --- | --- |
| Sessions | Map Hermes session/spawn APIs to Explorer/Worker/Reviewer/Verifier task cards |
| State | Read/write `.codex-multi-agent/` via OpenClaw scripts or MCP coordinator |
| Panel | Optionally host `ide/multi-agent-panel` in a Hermes-native webview |
| Outcomes | Map Hermes log patterns to normalized codes in `adapters/_shared/worker_outcome.py` |

## Expected workflow

```text
Main (Hermes) → create_task_cards / MCP create_task
             → spawn Hermes worker session with task card prompt
             → record_result + audit_scope
             → generate_final_report
```

## Normalized error mapping (planned)

- Quota / budget strings → `quota_exhausted`
- Read-only workspace → `sandbox_readonly`
- Auth prompts → `auth_required`
- Network failures → `network_unavailable`
- Missing Hermes CLI → `tool_missing`
- Session timeouts → `timeout`

## Related

- OpenClaw reference: [`../../../adapters/openclaw/`](../../../adapters/openclaw/)
- MCP wiring: [`../../../mcp/multi-agent-coordinator/clients/openclaw.md`](../../../mcp/multi-agent-coordinator/clients/openclaw.md)
