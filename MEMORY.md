# Project Memory

> **Historical note (2026-05-26):** Entries before 2026-05-26 that show `review_complete=failed` from
> `run_local_demo.py` dogfood runs are expected noise. Those runs inject intentional negative reviewer
> sessions (`reviewer-false-demo` / `reviewer-thin-demo`, tasks T998/T999). New `--summarize` output
> excludes those sessions from MEMORY gate summaries; you can ignore the older lines below.

Append-only log of multi-agent decisions and run outcomes. Safe defaults:

- Do **not** store secrets, credentials, tokens, or `.env` contents.
- Keep entries short (one decision or outcome per line).
- Prefer file paths relative to the repo root.

## Example entries

- `[2026-05-25T12:00:00+00:00] run 20260525T064400Z: FizzBuzz case study | gates: verify_complete=passed | audit=passed | findings=0`
- `[2026-05-25T12:05:00+00:00] decision: Workers must list tools_used in result reports (mirrors files_read).`
- `[2026-05-25T12:10:00+00:00] decision: MCP record_finding entries merge with reviewer sync; never clobber source=mcp findings.`

Detailed per-run notes live under `.codex-multi-agent/memory/run-<id>.md`.
- [2026-05-25T13:39:30.003218+00:00] run 20260525T133928Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T13:39:50.437790+00:00] run 20260525T133947Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T13:39:54.956677+00:00] run 20260525T133953Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T13:40:00.443884+00:00] run 20260525T133958Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T13:40:23.258135+00:00] run 20260525T134022Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T13:40:29.422918+00:00] run 20260525T134027Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T13:59:29.939572+00:00] run 20260525T135928Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T13:59:51.124334+00:00] run 20260525T135949Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:00:01.108997+00:00] run 20260525T135959Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:00:22.147428+00:00] run 20260525T140020Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:00:29.595001+00:00] run 20260525T140026Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:53:26.972986+00:00] run 20260525T145325Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:53:58.387860+00:00] run 20260525T145357Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:54:05.367790+00:00] run 20260525T145402Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:54:45.943416+00:00] run 20260525T145444Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:55:15.262102+00:00] run 20260525T145514Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:55:21.515140+00:00] run 20260525T145519Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:57:39.964400+00:00] run 20260525T145736Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:58:07.298123+00:00] run 20260525T145805Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-25T14:58:13.864078+00:00] run 20260525T145812Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-26T00:30:43.024579+00:00] run 20260526T003041Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-26T00:33:20.202659+00:00] run 20260526T003317Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
- [2026-05-26T00:58:43.640937+00:00] run 20260526T005842Z: Dogfood OpenClaw adapter v1 mission control | gates: explorers_complete=passed, workers_complete=passed, review_complete=failed, verify_complete=passed, scope_audit=pending, final_delivery=pending | audit=pending | findings=1
