# Case study: GitHub issue — docstring typo fix

End-to-end narrative for a **real-world-shaped** OSS contribution: a user files a GitHub issue about a docstring typo, Main orchestrates four roles, and a Worker lands a one-line fix with Reviewer + Verifier sign-off.

This directory is a **walkthrough sample** (no live PR is opened). It mirrors how teams use multi-agent-coding against an external issue link.

## Scenario

**Issue:** [`mock-issue.md`](mock-issue.md) — reader reports that `parse_retry_after()` docstring says *"retrun"* instead of *"return"* (copy-paste from an old comment).

**Fix:** [`after.py`](after.py) corrects the docstring; [`before.py`](before.py) shows the starting tree.

## Roles (4 agents)

| Role | Session | Responsibility |
| --- | --- | --- |
| **Explorer** | `explorer-retry-utils` | Read `before.py`, confirm typo location, note no behavior change needed |
| **Worker** | `worker-retry-utils` | Edit docstring only; produce result JSON + [`mock-pr.md`](mock-pr.md) narrative |
| **Reviewer** | `reviewer-docs` | Verify scope (docs-only), `files_read` evidence, no drive-by edits |
| **Verifier** | `verifier` | Run `python3 -m py_compile` on `after.py`; confirm gates in [`summary/run-summary.md`](summary/run-summary.md) |

## Artifacts

| Path | Purpose |
| --- | --- |
| [`cards/`](cards/) | Task cards T001–T004 |
| [`mock-issue.md`](mock-issue.md) | Simulated GitHub issue body |
| [`mock-pr.md`](mock-pr.md) | Simulated PR description (Worker output) |
| [`before.py`](before.py) / [`after.py`](after.py) | Code before/after |
| [`summary/run-summary.md`](summary/run-summary.md) | Post-run gate snapshot |

## Golden path (local replay)

```bash
# From repo root — generate cards into a temp state dir (optional)
python3 adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml adapters/openclaw/examples/favorite-feature.yaml \
  --out /tmp/gh-typo-mc --workspace-root "$(pwd)/examples/case-study-gh-issue-typo"

# Or use the checked-in cards/ and hand-write results/ following case-study-fizzbuzz
```

See also: [case-study-fizzbuzz](../case-study-fizzbuzz/) (single-file) and [case-study-flask-cli](../case-study-flask-cli/) (multi-file).
