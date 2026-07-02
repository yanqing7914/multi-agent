# Development And Release Process

This project is a product, not just a prompt pack. Treat changes as releaseable software.

## Branch Model

Recommended flow:

```text
feature/<short-name> -> dev -> main -> tag vX.Y.Z -> GitHub Release
```

Rules:

- `main` is the stable release branch.
- `dev` is the integration branch for product work.
- Feature branches should target `dev` unless the change is a hotfix.
- Release PRs from `dev` to `main` must pass full CI.
- Tags use `vX.Y.Z` and trigger release packaging.

If the repository is run as trunk-based development, keep `main` protected and require PRs plus CI.

## CI Layers

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `ci-fast.yml` | PR/push to `dev` or `main` | Adapter self-checks, Codex native checks, installer checks |
| `ci-full.yml` | PR/push to `main`, manual | Bench, demos, package build, package content verification |
| `codex-review.yml` | PR to `dev` or `main` | Produces a Codex App native review checklist artifact |
| `release.yml` | `v*.*.*` tag or manual | Build release zips and upload GitHub Release assets |

## Required Local Checks

Before opening a PR:

```bash
make fast
python3 scripts/validate_all_adapters.py
python3 adapters/codex/scripts/prepare_native_plan.py --self-check
python3 adapters/codex/scripts/finalize_native_run.py --self-check
python3 scripts/verify_release_packages.py --self-check
```

Before a release:

```bash
make release-check
python3 scripts/build_skill_packages.py --version <version>
python3 scripts/verify_release_packages.py --version <version>
```

## Product Release Assets

Every release must publish these user-facing assets:

| Asset | Audience |
| --- | --- |
| `codex-multi-agent-skill-vX.Y.Z.zip` | Codex App / CLI users |
| `cursor-multi-agent-pack-vX.Y.Z.zip` | Cursor App / CLI users |
| `claude-code-multi-agent-pack-vX.Y.Z.zip` | Claude Code App / IDE / CLI users |
| `hermes-multi-agent-pack-vX.Y.Z.zip` | Hermes users |
| `openclaw-multi-agent-skill-vX.Y.Z.zip` | OpenClaw / Her users |
| `multi-agent-coding-skill-vX.Y.Z.zip` | Protocol/reference users |

`scripts/verify_release_packages.py` is the release gate for package contents.
It checks that client packages include native entrypoints, install manifests,
client-specific role agents where applicable, and shared mission-control scripts.
It also checks the content-governance denylist from
[`docs/content-governance.md`](content-governance.md), including CI internals,
developer-only docs, runtime state, generated zips, and common secret filenames.

## Codex Review Policy

Use Codex review as a release quality gate, not as a marketing claim.

- Every PR touching `SKILL.md`, `adapters/codex/`, `scripts/run_multi_agent.py`, `scripts/install_native_skills.py`, package building, or CI should receive a Codex native-path review.
- Review must confirm the project still says "prompt-guided coordination", not real sandboxing.
- Review must confirm Workers cannot silently expand `allowed_paths`, `blocked_commands`, or `may_use_skills`.
- Review must confirm App users have a native path and CLI bridge users have deterministic commands.
- Review findings should be fixed before merging into `main`; unresolved findings must be documented in the PR.

## Codex App Native Acceptance

Changes touching `adapters/codex/`, `scripts/run_multi_agent.py`, native installation, or task-card contracts must verify:

- `codex-native-plan` emits records with `spawn_agent_payload`.
- `spawn_agent_payload` includes custom `agent_type`, prompt source, lifecycle, and authorized skill items.
- Main lifecycle remains explicit: spawn, wait, optional repair input, collect result reports, close agent.
- `finalize_native_run.py` blocks final delivery when reports or scope audit are missing.
- Custom agents install to `~/.codex/agents`.
- Safety wording does not claim OS-level isolation.

## Release Checklist

- [ ] Version updated in `pyproject.toml`, README badges/links, and CHANGELOG.
- [ ] `scripts/validate_all_adapters.py` passes.
- [ ] Release packages build with `scripts/build_skill_packages.py --version <version>`.
- [ ] `scripts/verify_release_packages.py --version <version>` passes.
- [ ] Fresh install from the Codex package passes `scripts/install_native_skills.py --client codex --check`.
- [ ] GitHub tag `vX.Y.Z` is pushed.
- [ ] GitHub Release contains all generated `dist/*-vX.Y.Z.zip` files.

## Runtime State

Do not commit runtime state unless it is an intentional public demo fixture:

- `.codex-multi-agent*/`
- local auth files
- secret-bearing logs
- generated package staging directories

Use `--state-dir` to place temporary multi-agent state outside a project when needed.
