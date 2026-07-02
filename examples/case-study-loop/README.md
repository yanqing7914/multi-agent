# Case study: loop engineering with `run_loop.py`

A focused walkthrough of **loop engineering**: how to drive a Worker inside a
*controlled* loop until an **independent** verifier is satisfied — or a hard
budget stops it — instead of either a single best-effort pass or an unbounded
"keep trying" loop.

The engine is [`adapters/openclaw/scripts/run_loop.py`](../../adapters/openclaw/scripts/run_loop.py).
It is dependency-free and ships in every client pack (under `adapters/openclaw/scripts/`).

## The idea: maker → independent checker → repair, bounded

A reliable agent loop has five elements and one hard rule:

| Element | In `run_loop` | What it means here |
| --- | --- | --- |
| **Goal** | the echoed `goal` + stop condition | an explicit, *verifiable* success test, not a vibe |
| **Actions** | `maker(iteration, last_feedback)` | one production step per round (the Worker) |
| **Verify** | `verifier(maker_output) -> (passed, feedback)` | an **independent** judge of the output |
| **Repair** | previous `feedback` is passed to the next `maker` | diagnose-then-adjust, not blind retry |
| **Memory** | one record appended to `memory` per round | lessons persist across iterations |

**Hard rule — maker ≠ checker.** The producer may not grade itself. If the same
callable is passed as both `maker` and `verifier`, the run is rejected up front
(`status="rejected"`, `maker_is_checker_violation=true`, zero iterations).

**Stop condition (always bounded).** The loop ends when the verifier passes, or
when `--max-iterations` / a `budget` cap (`max_seconds`, `max_cost`) is reached.
It is never unbounded.

## How it maps to our roles

| Loop concept | Framework role / artifact |
| --- | --- |
| `maker` (Actions) | **Worker** — `run_loop` dispatches the Worker task card via `scripts/run_multi_agent.py` each round |
| `verifier` (Verify) | **Verifier / audit (the checker)** — `--verify-command` (e.g. `pytest -q`), optionally AND-ed with `audit_worker_output.py` via `--with-audit` |
| `last_feedback` (Repair) | verifier output (`rc`, stdout/stderr tail, audit detail) threaded into the next Worker round |
| `memory` (Memory) | per-round log of pass/feedback/output — the same idea as `MEMORY.md` for cross-run lessons |
| stop / gate | the **gate**: verifier-pass = stop; `max-iterations`/budget = bounded stop |

Because the Worker is the maker and the Verifier + scope audit are the checker,
maker ≠ checker is satisfied by construction: the agent that writes code is not
the thing that decides the code is done.

## Deterministic demo (no side effects)

Run the built-in self-check. It is fully deterministic, touches no repo files,
and never invokes an external CLI — ideal as a smoke test or CI gate:

```bash
python3 adapters/openclaw/scripts/run_loop.py --self-check
```

Expected output:

```json
{
  "ok": true,
  "message": "run_loop self-check passed"
}
```

That self-check exercises the whole contract with fake maker/verifier callables:

- **Convergence** — a maker that improves each round makes the verifier pass on
  iteration *k*, and `status="passed"`, `iterations_run==k`.
- **Bounded exhaustion** — a never-passing verifier stops exactly at
  `max_iterations` with `status="exhausted"` (proof: no infinite loop).
- **Repair threading** — round *n*'s maker receives round *n-1*'s feedback
  (`[None, "fix-1", "fix-2", …]`).
- **maker ≠ checker** — one callable used for both is rejected with
  `maker_is_checker_violation=true` and zero iterations.
- **Memory** — one ordered record per round is appended.
- **Budget** — `max_cost` / `max_seconds` cap the loop independently of
  `max_iterations`.
- **Guard rails / robustness** — `max_iterations < 1` and non-list memory are
  rejected; tuple/bool/dict verdict shapes normalize; a maker that raises is
  captured as repair feedback and the loop stays bounded; and real-mode
  plumbing rejects a missing `--verify-command`, missing `--task-card`, or a
  nonexistent card **without running anything**.

## Real, verifier-gated convergence loop

Once you have task cards (see Step 3 below), wire a real loop. The maker
re-dispatches the Worker card; the verifier runs your command and (with
`--with-audit`) also requires the scope-audit gate to pass:

```bash
python3 adapters/openclaw/scripts/run_loop.py \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --runtime openclaw \
  --verify-command "pytest -q" \
  --with-audit \
  --max-iterations 5 \
  --state-dir .codex-multi-agent
```

Behavior:

- Each round runs the Worker, then runs `pytest -q` (returncode 0 ⇒ passed).
- `--with-audit` AND-s in `audit_worker_output.py`: even if tests pass, a scope
  violation keeps the goal unmet, so the loop keeps repairing.
- The loop stops at the first round where the verifier passes, otherwise after
  5 iterations (`status="exhausted"`). Add `--budget-seconds` / `--budget-cost`
  to tighten the cap, or `--timeout` to bound each subprocess.

Useful flags (all real-mode):

| Flag | Purpose |
| --- | --- |
| `--task-card` | Worker card the maker dispatches via `run_multi_agent.py` (required) |
| `--verify-command` | shell command; returncode 0 ⇒ verifier passed (required) |
| `--with-audit` | AND the verifier with `audit_worker_output.py` ok |
| `--max-iterations` | hard upper bound on rounds (default 5) |
| `--runtime` | runtime for `run_multi_agent.py` (default `openclaw`) |
| `--state-dir` | mission-control dir for the audit gate (default `.codex-multi-agent`) |
| `--budget-seconds` / `--budget-cost` | optional wall-clock / cost caps |

## Copyable end-to-end loop

From the target repo root (after installing the pack and, if needed, configuring MCP):

```bash
# 0) Smoke test the engine — deterministic, no side effects
python3 adapters/openclaw/scripts/run_loop.py --self-check

# 1) Generate scoped task cards into .codex-multi-agent/
python3 adapters/openclaw/scripts/create_task_cards.py \
  --task "Fix the backend bug and keep tests green" \
  --mode fix \
  --modules backend tests \
  --reviewers correctness \
  --review-skill ssrd \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent

# 2) Drive the verifier-gated loop on the backend Worker card
python3 adapters/openclaw/scripts/run_loop.py \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --runtime openclaw \
  --verify-command "pytest -q" \
  --with-audit \
  --max-iterations 5 \
  --state-dir .codex-multi-agent

# 3) Main's authoritative scope audit before delivery
python3 adapters/openclaw/scripts/capture_changed_files.py --state-dir .codex-multi-agent  # staged + unstaged + untracked
python3 adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

## Why this is safer than "just retry"

- **Independent verification** — the checker is a different process from the
  maker, and `--with-audit` adds a scope gate, so "tests pass" can't mask an
  out-of-bounds edit.
- **Bounded by design** — there is always a hard stop; non-convergence ends in
  `exhausted`, not a runaway loop.
- **Repair, not retry** — each failure's feedback is fed forward, so the next
  Worker round is informed instead of identical.
- **Auditable** — `history`, `memory`, `budget_spent`, and `stop_reason` are all
  in the JSON result, so Main can see exactly why the loop stopped.

## Related

- End-to-end install + run: [`../end-to-end-agent-install/`](../end-to-end-agent-install/)
- Engine source: [`../../adapters/openclaw/scripts/run_loop.py`](../../adapters/openclaw/scripts/run_loop.py)
- Other case studies: [`../case-study-fizzbuzz/`](../case-study-fizzbuzz/), [`../case-study-flask-cli/`](../case-study-flask-cli/), [`../case-study-gh-issue-typo/`](../case-study-gh-issue-typo/)
