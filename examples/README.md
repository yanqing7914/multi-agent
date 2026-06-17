# Examples

This directory contains lightweight workflow examples and complete case studies
for `multi-agent-coding`.

## Workflow Examples

| File | Purpose |
| --- | --- |
| [`feature.md`](feature.md) | Multi-module feature flow: Explorer -> Worker -> Reviewer -> Verifier |
| [`bugfix.md`](bugfix.md) | Bugfix flow: investigate first, then make scoped changes |
| [`review.md`](review.md) | Read-only multi-reviewer flow with review skills such as `ssrd` |

## End-to-End Install Demo

| Case | Purpose |
| --- | --- |
| [`end-to-end-agent-install/`](end-to-end-agent-install/) | User sends the GitHub link to an agent, the agent installs the right package, then starts a scoped multi-agent run |

## Case Studies

| Case | Purpose | Key Artifacts |
| --- | --- | --- |
| [`case-study-fizzbuzz/`](case-study-fizzbuzz/) | Dogfood OpenClaw v1 task control on a small FizzBuzz module | `cards/`, `results/`, `summary/run-summary.md` |
| [`case-study-flask-cli/`](case-study-flask-cli/) | Multi-file Flask-shaped CLI case with real adapter runs | `app/`, `tests/`, `task.yaml`, `.runs/` |
| [`case-study-gh-issue-typo/`](case-study-gh-issue-typo/) | Simulated GitHub issue -> Explorer -> Worker -> Reviewer -> Verifier | `mock-issue.md`, `mock-pr.md`, `cards/` |

## Related

- OpenClaw adapter: [`../adapters/openclaw/README.md`](../adapters/openclaw/README.md)
- Codex adapter: [`../adapters/codex/README.md`](../adapters/codex/README.md)
- Cursor adapter: [`../adapters/cursor/README.md`](../adapters/cursor/README.md)
- Claude adapter: [`../adapters/claude-code/README.md`](../adapters/claude-code/README.md)
- Bench harness: [`../bench/README.md`](../bench/README.md)
