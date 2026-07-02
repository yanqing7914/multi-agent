# Governance

This document defines how `multi-agent` is maintained as a product-quality open-source project.

## Branch Model

Recommended flow:

```text
feature/<short-name> -> dev -> main -> tag vX.Y.Z -> GitHub Release
```

Rules:

- `main` is stable and releaseable.
- `dev` is the integration branch for product work.
- Feature branches target `dev` by default.
- Hotfix branches may target `main` when they only fix release-blocking issues.
- Tags must use `vX.Y.Z` and should point at `main`.

## Required Checks

Every PR should pass fast CI:

```bash
make fast
```

Release or main-branch PRs should pass full CI:

```bash
make full
make release-check
```

The authoritative CI workflows are:

| Workflow | Purpose |
| --- | --- |
| `ci-fast.yml` | Fast validation for PRs and pushes to `dev` / `main` |
| `ci-full.yml` | Product validation, package build, package verification |
| `codex-review.yml` | Codex native-path review checklist artifact |
| `release.yml` | Tag/manual release package build and GitHub Release upload |

## Review Policy

At least one maintainer review is required for:

- root `SKILL.md`
- any `adapters/**/SKILL.md`
- `scripts/build_skill_packages.py`
- `scripts/verify_release_packages.py`
- `scripts/install_native_skills.py`
- `.github/workflows/**`
- release documentation

Codex-native path review is required when changes touch:

- `adapters/codex/**`
- native subagent planning/finalization
- Worker/Reviewer result contracts
- `allowed_paths`, `blocked_commands`, or `may_use_skills`
- package installation behavior for Codex

## Release Policy

Before tagging:

1. Update version references.
2. Update `CHANGELOG.md`.
3. Run `make release-check`.
4. Confirm release packages exclude forbidden files.
5. Push tag `vX.Y.Z`.
6. Confirm GitHub Release includes all expected zip assets.

Release artifacts are product deliverables. The source repository may contain developer docs and CI config; client packages must remain curated and minimal.

## Security And Secrets

Never commit:

- `.env*`
- tokens or auth files
- private keys or certificates
- real user logs containing credentials
- local runtime state such as `.codex-multi-agent*/`

If a secret is committed, rotate it immediately and remove it from history before release.

## Decision Records

Use `MEMORY.md` for lightweight project memory and `CHANGELOG.md` for release-visible changes. Large architectural decisions should be documented under `docs/`.
