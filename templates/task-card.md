# Task Card

Task ID:
Mode: research | implement | fix | review | refactor
Role: Explorer | Worker | Reviewer | Verifier
Title:

## Objective

## Context

## Dependencies

## Target
- Type: code | diff | plan | document | artifact
- Paths or summary:

## Allowed Paths
- 

## Forbidden Paths
- .env
- .env.*
- .npmrc
- .pypirc
- .netrc
- ~/.ssh/**
- ~/.codex/auth.json
- **/*.pem
- **/*.key

## Allowed Commands
- rg / file listing / read-only inspection
- project-specific tests if listed here

## Blocked Commands
- dependency install
- deploy / publish / release
- git push / git reset --hard / force-push
- destructive delete
- production migration
- credential sync/export

## Skill Policy
may_use_skills:
- 
forbidden_skills:
- credential access
- deployment
- global config mutation
- git history rewriting
network_skills_require_main_approval: true
install_skills_require_main_approval: true
secret_access_skills_forbidden: true

## Subagent Policy
may_spawn_subagents: false
subagent_budget: 0
allowed_subagent_roles: []

## Acceptance Criteria
- 

## Validation Required
- 

## Stop Conditions
- Need to edit outside allowed paths
- Need to read a forbidden path or secret value
- Need to install dependencies or use network unexpectedly
- Need to deploy, publish, or mutate production data
- Tests fail for unclear or unrelated reasons
- User changes may be overwritten

## Output Required
- Findings or changed files
- Evidence or implementation notes
- Validation performed
- Risks, blockers, and handoff notes
