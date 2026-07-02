# Recommended Branch Protection

Configure these rules in GitHub repository settings.

## `main`

- Require pull request before merging.
- Require at least 1 approving review.
- Require review from CODEOWNERS.
- Dismiss stale approvals when new commits are pushed.
- Require status checks:
  - `Fast validation (3.11)`
  - `Fast validation (3.12)`
  - `Full product validation`
  - `Native-path review checklist`
- Require branches to be up to date before merging.
- Restrict force pushes.
- Restrict deletions.

## `dev`

- Require pull request before merging.
- Require at least 1 approving review.
- Require status checks:
  - `Fast validation (3.11)`
  - `Fast validation (3.12)`
  - `Native-path review checklist`
- Restrict force pushes.
- Restrict deletions.

## Release Tags

- Tags should be created from `main`.
- Tag format: `vX.Y.Z`.
- Release workflow must pass before publishing assets.
