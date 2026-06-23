# Hermes MCP registration

Hermes Agent has a native MCP client configured in `~/.hermes/config.yaml` under
the top-level `mcp_servers:` key. Register the coordinator there (stdio).

## Option A — edit `~/.hermes/config.yaml` directly

Copy the block from [`hermes-mcp.yaml`](hermes-mcp.yaml) into your config, merged
under `mcp_servers:` (keep any existing servers):

```yaml
mcp_servers:
  multi-agent-coordinator:
    type: stdio
    command: python3
    args:
      - "{REPO_ROOT}/mcp/multi-agent-coordinator/server.py"
      - "--state-dir"
      - "{WORKSPACE_ROOT}/.codex-multi-agent"
    env:
      WORKSPACE: "{WORKSPACE_ROOT}"
```

Replace the placeholders before saving:

- `{REPO_ROOT}` — absolute path to this `multi-agent-coding` checkout.
- `{WORKSPACE_ROOT}` — absolute path to the project you are dogfooding (where
  `.codex-multi-agent/` lives).

## Option B — use a native-mcp skill

If your Hermes install exposes a `native-mcp` (or equivalent) skill for
registering MCP servers, point it at [`hermes-mcp.yaml`](hermes-mcp.yaml) and let
it merge the entry under `mcp_servers:` for you. The skill still expects the same
`command` / `args` / `env` shape shown above.

## State directory resolution

The server resolves its state directory in this order (first match wins):

1. `--state-dir` argument — the snippet pins it to `{WORKSPACE_ROOT}/.codex-multi-agent`.
2. `WORKSPACE` env var — falls back to `$WORKSPACE/.codex-multi-agent` when
   `--state-dir` is omitted (the `env:` block sets this as a backstop).
3. Current working directory — `./.codex-multi-agent` if neither is provided.

Keeping both `--state-dir` and `env.WORKSPACE` pinned to the same workspace makes
the resolution deterministic regardless of how Hermes launches the process.

## Verify

```bash
python3 mcp/multi-agent-coordinator/scripts/serve.py --self-check
python3 mcp/multi-agent-coordinator/scripts/self_check.py
```

See [`../README.md`](../README.md).
