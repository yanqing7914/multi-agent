"""Shared --runtime allowed values for OpenClaw scripts and bench harnesses."""

from __future__ import annotations

# Task card generator (sessions_spawn runtime= on cards)
TASK_CARD_RUNTIME_CHOICES: tuple[str, ...] = (
    "acp",
    "subagent",
    "native",
    "codex",
    "cursor",
    "claude-code",
)

# Local bench + swebench-lite harness
BENCH_RUNTIME_CHOICES: tuple[str, ...] = (
    "codex",
    "cursor",
    "claude",
    "claude-code",
    "openclaw",
    "dry",
    "dry-runtime",
)

# Cross-adapter launcher (scripts/run_multi_agent.py)
LAUNCHER_RUNTIME_CHOICES: tuple[str, ...] = (
    "openclaw",
    "cursor-desktop",
    "cursor",
    "codex-native",
    "codex-desktop",
    "codex",
    "claude-desktop",
    "claude-code",
)

# run_local_demo.py simulated spawn runtime
DEMO_SPAWN_RUNTIME = "subagent"


def runtime_consistency_self_check() -> list[str]:
    """Ensure bench runtimes are a superset of task-card client runtimes where applicable."""
    errors: list[str] = []
    for client in ("codex", "cursor", "claude-code"):
        if client not in BENCH_RUNTIME_CHOICES:
            errors.append(f"BENCH_RUNTIME_CHOICES missing {client}")
        if client not in TASK_CARD_RUNTIME_CHOICES:
            errors.append(f"TASK_CARD_RUNTIME_CHOICES missing {client}")
    if "native" not in TASK_CARD_RUNTIME_CHOICES:
        errors.append("TASK_CARD_RUNTIME_CHOICES missing native")
    if "dry-runtime" not in BENCH_RUNTIME_CHOICES:
        errors.append("BENCH_RUNTIME_CHOICES missing dry-runtime")
    return errors
