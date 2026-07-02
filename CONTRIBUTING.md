# Contributing

Thanks for improving **multi-agent**. This repository is maintained as a product-quality multi-agent coding framework: changes should be scoped, reproducible, auditable, and safe to package.

## Start Here

- Product definition: [`docs/product.md`](docs/product.md)
- Governance: [`docs/governance.md`](docs/governance.md)
- Content governance: [`docs/content-governance.md`](docs/content-governance.md)
- Development and release process: [`docs/development.md`](docs/development.md)
- Client support model: [`docs/clients.md`](docs/clients.md)

## Branch Flow

Use:

```text
feature/<short-name> -> dev -> main -> tag vX.Y.Z -> GitHub Release
```

- Target `dev` for normal features and product work.
- Target `main` only for release hotfixes.
- Do not force-push shared branches.
- Release tags must be created from `main`.

## Local Setup

The project intentionally uses Python stdlib for runtime scripts.

```bash
cd /path/to/multi-agent-coding
python3 -V
```

Optional editable install:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Required Checks

Before opening a PR:

```bash
make fast
```

For release-impacting changes:

```bash
make full
make release-check
```

Equivalent commands:

```bash
python3 scripts/validate_all_adapters.py
python3 scripts/verify_release_packages.py --self-check
python3 scripts/build_skill_packages.py --version 0.0.0-local
python3 scripts/verify_release_packages.py --version 0.0.0-local
```

## Pull Requests

Use the PR template and include:

- user-visible summary
- affected clients
- checks run
- release impact
- Codex App native-path review when relevant

Required review areas:

- `SKILL.md` and adapter `SKILL.md` files
- native subagent contracts
- install/package scripts
- CI/CD workflows
- content governance and release packaging

## Adding A Client Adapter

1. Add `adapters/<client>/SKILL.md`, `README.md`, `QUICKSTART.md`, and scripts.
2. Reuse OpenClaw mission-control scripts instead of copying gate logic.
3. Register the runtime in `scripts/run_multi_agent.py`.
4. Add a deterministic self-check and wire it into `scripts/validate_all_adapters.py`.
5. Update `docs/clients.md`, `README.md`, and package building rules.
6. Add package verification requirements in `scripts/verify_release_packages.py`.

## Package And Content Rules

Client release packages are curated products, not full source snapshots.

- Use allowlists in `scripts/build_skill_packages.py`.
- Use required-file and forbidden-file checks in `scripts/verify_release_packages.py`.
- Keep developer-only docs out of client packages.
- Keep runtime state and generated artifacts out of git.

Never commit:

- `.codex-multi-agent*/`
- `.env*`
- auth files, tokens, private keys, certificates
- large private logs or proprietary code excerpts
- generated CI/test zip packages

## Issues

- Use `.github/ISSUE_TEMPLATE/bug_report.md` for bugs.
- Use `.github/ISSUE_TEMPLATE/feature_request.md` for feature requests.
- Include reproduction commands and relevant doctor/validation output when possible.

## Maintainers

Maintainer: [@yanqing7914](https://github.com/yanqing7914)
