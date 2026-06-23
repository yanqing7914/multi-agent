#!/usr/bin/env python3
"""Hermes adapter contract self-check (dependency-free, stdlib only, Python 3.10+).

Validates the Hermes adapter's portable contract without spawning any agent or
runtime. Style mirrors adapters/cursor/scripts/cursor_self_check.py and
adapters/_shared/self_check.py (JSON payload + errors list + exit code), but the
checks are self-contained so this script has no third-party or cross-module
dependencies.

Checks:
  - SKILL.md / README.md / QUICKSTART.md exist under the adapter root
  - SKILL.md has YAML frontmatter declaring `name` and `description`
  - SKILL.md documents the `mcp_servers` wiring snippet
  - SKILL.md documents agentskills.io discovery (the `agentskills` keyword)

Pass prints {"ok": true, ...} and exits 0; failure prints the errors and exits 1.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ADAPTER_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_DOCS = ("SKILL.md", "README.md", "QUICKSTART.md")


def read_text(path: Path) -> str:
    # utf-8-sig tolerates a stray BOM without changing the content otherwise.
    return path.read_text(encoding="utf-8-sig")


def extract_frontmatter(text: str) -> str | None:
    """Return the YAML frontmatter block delimited by leading/closing `---`."""
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index])
    return None


def frontmatter_has_key(frontmatter: str, key: str) -> bool:
    """True when a top-level `key:` is present with a non-empty value."""
    prefix = f"{key}:"
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix) and stripped[len(prefix):].strip():
            return True
    return False


def run_self_check(adapter_root: Path) -> int:
    errors: list[str] = []
    checked: list[str] = []

    for name in REQUIRED_DOCS:
        path = adapter_root / name
        if path.is_file():
            checked.append(name)
        else:
            errors.append(f"missing file: {path}")

    skill_path = adapter_root / "SKILL.md"
    if skill_path.is_file():
        skill_text = read_text(skill_path)
        frontmatter = extract_frontmatter(skill_text)
        if frontmatter is None:
            errors.append("SKILL.md missing YAML frontmatter (--- ... ---)")
        else:
            for key in ("name", "description"):
                if not frontmatter_has_key(frontmatter, key):
                    errors.append(f"SKILL.md frontmatter missing {key}")
        if "mcp_servers" not in skill_text:
            errors.append("SKILL.md missing mcp_servers snippet keyword")
        if "agentskills" not in skill_text:
            errors.append("SKILL.md missing agentskills keyword")

    payload = {
        "ok": not errors,
        "adapter": "hermes",
        "adapter_root": str(adapter_root),
        "checked": checked,
        "errors": errors,
    }
    print(json.dumps(payload, indent=2))
    return 0 if not errors else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-check", action="store_true", help="Run built-in validation and exit")
    parser.parse_args()
    # The self-check is this script's only behavior; run it with or without the flag.
    return run_self_check(ADAPTER_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
