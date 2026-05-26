# Mission-control task panel (v3)

Local read-only web UI for `.codex-multi-agent/` mission-control state. No build step, no npm — vanilla HTML/CSS/JS plus a small Python stdlib HTTP server.

## Launch

From any workspace with a `.codex-multi-agent/` directory:

```bash
python3 ide/multi-agent-panel/server.py --state-dir .codex-multi-agent --port 9876
```

Open [http://127.0.0.1:9876/](http://127.0.0.1:9876/)

### Options

| Flag | Default | Purpose |
| --- | --- | --- |
| `--state-dir` | `.codex-multi-agent` | State directory to watch |
| `--port` | `9876` | HTTP port |
| `--host` | `127.0.0.1` | Bind address (local only) |
| `--refresh` | `5` | Default UI poll interval (seconds) |
| `--write` | off | Enable POST mutation endpoints |

## What it shows

- **Run header** — task title, run id, current phase, last sync time
- **Gate status** — Explorer / Worker / Reviewer / Verifier / scope_audit / final_delivery badges
- **Tasks** — id, role, session, status, result report links, preflight issues
- **Findings** — severity, title, file:line when present
- **Latest audit** — gate, violations, warnings, audit path, changed-files digest, stale flag
- **Preflight / workspace issues**
- **Final delivery summary preview** — from `summary/run-summary.md`

The UI polls `GET /api/state` every N seconds (configurable in the page).

## API

| Endpoint | Method | Description |
| --- | --- | --- |
| `/api/state` | GET | Full dashboard payload |
| `/api/findings` | GET | Findings only |
| `/api/config` | GET | Poll interval + write flag |
| `/api/sync` | POST | Run `update_task_status.py --sync` (**`--write` only**) |
| `/api/audit` | POST | Run `audit_worker_output.py --write-audit` (**`--write` only**) |
| `/api/summarize` | POST | Run `update_task_status.py --summarize` (**`--write` only**) |

## Security

- **Read-only by default** — no state mutation unless you pass `--write`.
- **Local bind** — defaults to `127.0.0.1`; do not expose to untrusted networks without a reverse proxy and auth.
- **Write endpoints** spawn local Python subprocesses against your workspace scripts only.

## Screenshots

<!-- TODO: add screenshot of gate board + findings panel after dogfood run -->

_Placeholder: capture from a real `.codex-multi-agent-real-dogfood` run._

## Self-check

```bash
python3 ide/multi-agent-panel/scripts/self_check.py
```

See [`docs/roadmap.md`](../../docs/roadmap.md).
