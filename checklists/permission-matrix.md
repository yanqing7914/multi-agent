# Permission Matrix Checklist

Before delegating, define for each task:

- Role and mode.
- Read scope.
- Write scope or `write_permission: false`.
- Allowed paths.
- Forbidden paths.
- Allowed commands.
- Blocked commands.
- Allowed skills.
- Skills requiring main-agent approval.
- Subagent policy.
- Validation requirement.
- Stop conditions.

Default role permissions:

| Role | Write | Commands | Skills | Subagents |
| --- | --- | --- | --- | --- |
| Explorer | Never | Read-only | Read-only only | No |
| Reviewer | Never | Read-only | Review only | No |
| Worker | `allowed_paths` only | Limited | Task-card only | No by default |
| Verifier | No by default | Test/build only | Testing only | No |
| Main | As needed | As environment allows | Any safe/authorized | Yes |
