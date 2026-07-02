"""pip-installable entrypoint for the multi-agent-coding skill pack.

The real product is the prompt/skill tree (SKILL.md + adapters + scripts +
tools). This package bundles that tree and exposes a thin `multi-agent-coding`
CLI that forwards to the bundled scripts, so `pip install multi-agent-coding`
is enough to run doctor/install/task-card workflows anywhere.
"""

__version__ = "0.3.1"
