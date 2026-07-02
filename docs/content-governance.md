# Content Governance

This repository is open source, but not every file is a user-facing product artifact. Content is governed by audience, release-package inclusion, and safety risk.

## Audience Classes

| Class | Audience | Examples | Public repo | Client release zip |
| --- | --- | --- | --- | --- |
| User entry | End users and their agents | `README.md`, `dist/README.md`, `docs/agent-install.md`, adapter `QUICKSTART.md` | Yes | Yes |
| Runtime contract | Agents executing work | `SKILL.md`, adapter `SKILL.md`, `templates/`, `checklists/` | Yes | Yes |
| Product reference | Users, maintainers, reviewers | `docs/product.md`, `docs/clients.md`, `docs/architecture.md`, `docs/roadmap.md` | Yes | Generic package only unless needed |
| Developer maintenance | Maintainers and contributors | `docs/development.md`, `.github/`, `Makefile`, CI config | Yes | No |
| Test and benchmark | Maintainers and evaluators | `bench/`, heavy demos, offline fixtures | Yes when sanitized | No for client packages |
| Experimental | Maintainers | `docs/experimental/`, prototype examples | Optional | No stable release zip |
| Runtime state | Local runs only | `.codex-multi-agent/`, `.runs/`, worker logs | No, except sanitized demo fixtures | Never |
| Sensitive material | Nobody | tokens, `.env`, auth files, private keys, secret logs | Never | Never |

## Public Entry Rules

- `README.md` should stay user-oriented: what it is, which zip to download, how to install, how to verify, and what the product does not guarantee.
- `docs/agent-install.md` is written for agents. It should tell an agent how to pick a client-specific package from the GitHub link.
- Client `QUICKSTART.md` files should be short and operational.
- Developer workflow belongs in `docs/development.md`, not in the user path.
- Product boundaries and v1.0 acceptance criteria belong in `docs/product.md`.

## Release Package Rules

Client-specific packages are curated product artifacts. They should include only the files needed by that client:

- native `SKILL.md`, `README.md`, and `QUICKSTART.md`
- client adapter files
- shared mission-control scripts
- `templates/` and `checklists/`
- installer, doctor, launcher, and required tool wrappers
- native Worker / Reviewer agent files where supported

Client packages must not include:

- `.github/`
- `bench/`
- `docs/development.md`
- `docs/content-governance.md`
- `.codex-multi-agent*`
- `dist/`
- `.env*`, auth files, private keys, local logs
- generated package staging directories

The generic `multi-agent-coding-skill` package may include public product reference docs, but it must still exclude maintenance internals, CI files, runtime state, secrets, and old release zips.

## Enforcement

`scripts/build_skill_packages.py` uses explicit allowlists. Do not switch it to "zip the repo".

`scripts/verify_release_packages.py` enforces both:

- required files per release package
- forbidden paths and sensitive filenames

CI runs the verifier in fast/full/release workflows. Any new package type must add both required and forbidden checks before release.

## Adding New Content

Before adding a file, answer:

1. Who is the audience?
2. Should it be in the public repository?
3. Should it be in client release zips?
4. Could it contain secrets, private code excerpts, or local paths?
5. Which verifier or `.gitignore` rule protects it?

If unsure, default to public source documentation but exclude it from client release zips.
