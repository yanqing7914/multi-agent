#!/usr/bin/env python3
"""Verify generated release packages contain required product files."""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST = REPO_ROOT / "dist"

REQUIRED_BY_PACKAGE = {
    "codex-multi-agent-skill": [
        "codex-multi-agent/SKILL.md",
        "codex-multi-agent/INSTALL.json",
        "codex-multi-agent/NATIVE_SUBAGENT_CONTRACT.md",
        "codex-multi-agent/adapters/codex/scripts/prepare_native_plan.py",
        "codex-multi-agent/adapters/codex/scripts/finalize_native_run.py",
        "codex-multi-agent/adapters/codex/scripts/dogfood_codex_app.py",
        "codex-multi-agent/adapters/codex/agents/multi-agent-worker.toml",
        "codex-multi-agent/adapters/codex/agents/multi-agent-reviewer.toml",
        "codex-multi-agent/scripts/run_multi_agent.py",
        "codex-multi-agent/scripts/doctor.py",
        "codex-multi-agent/adapters/openclaw/scripts/capture_changed_files.py",
    ],
    "cursor-multi-agent-pack": [
        "cursor-multi-agent/SKILL.md",
        "cursor-multi-agent/INSTALL.json",
        "cursor-multi-agent/cursor-rules.md",
        "cursor-multi-agent/scripts/run_multi_agent.py",
        "cursor-multi-agent/adapters/openclaw/scripts/capture_changed_files.py",
    ],
    "claude-code-multi-agent-pack": [
        "claude-code-multi-agent/SKILL.md",
        "claude-code-multi-agent/INSTALL.json",
        "claude-code-multi-agent/CLAUDE.md",
        "claude-code-multi-agent/adapters/claude-code/agents/multi-agent-worker.md",
    ],
    "hermes-multi-agent-pack": [
        "hermes-multi-agent/SKILL.md",
        "hermes-multi-agent/INSTALL.json",
        "hermes-multi-agent/adapters/hermes/SKILL.md",
    ],
    "openclaw-multi-agent-skill": [
        "openclaw-multi-agent/SKILL.md",
        "openclaw-multi-agent/README.md",
        "openclaw-multi-agent/scripts/create_task_cards.py",
        "openclaw-multi-agent/scripts/audit_worker_output.py",
        "openclaw-multi-agent/scripts/capture_changed_files.py",
        "openclaw-multi-agent/scripts/_locking.py",
        "openclaw-multi-agent/templates/task-card.md",
    ],
    "multi-agent-coding-skill": [
        "multi-agent-coding/SKILL.md",
        "multi-agent-coding/README.md",
        "multi-agent-coding/docs/agent-install.md",
        "multi-agent-coding/templates/task-card.md",
    ],
}

FORBIDDEN_ANYWHERE = [
    ".env",
    ".env.",
    ".git/",
    ".github/",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "__pycache__/",
    ".package-stage/",
    ".codex-multi-agent",
    ".runs/",
    "id_rsa",
    "id_ed25519",
]

FORBIDDEN_BY_PACKAGE = {
    "codex-multi-agent-skill": [
        ".github/",
        "bench/",
        "dist/",
        "docs/content-governance.md",
        "docs/development.md",
        "docs/governance.md",
    ],
    "cursor-multi-agent-pack": [
        ".github/",
        "bench/",
        "dist/",
        "docs/content-governance.md",
        "docs/development.md",
        "docs/governance.md",
    ],
    "claude-code-multi-agent-pack": [
        ".github/",
        "bench/",
        "dist/",
        "docs/content-governance.md",
        "docs/development.md",
        "docs/governance.md",
    ],
    "hermes-multi-agent-pack": [
        ".github/",
        "bench/",
        "dist/",
        "docs/content-governance.md",
        "docs/development.md",
        "docs/governance.md",
    ],
    "openclaw-multi-agent-skill": [
        ".github/",
        "bench/",
        "dist/",
        "docs/content-governance.md",
        "docs/development.md",
        "docs/governance.md",
    ],
    "multi-agent-coding-skill": [
        ".github/",
        "bench/",
        "dist/",
        "docs/development.md",
        "docs/governance.md",
    ],
}


def find_package(prefix: str, version: str | None) -> Path | None:
    pattern = f"{prefix}-v{version}.zip" if version else f"{prefix}-v*.zip"
    matches = sorted(DIST.glob(pattern))
    return matches[-1] if matches else None


def matches_forbidden(name: str, pattern: str) -> bool:
    parts = name.split("/")
    basename = parts[-1]
    if pattern.endswith("/"):
        needle = pattern.strip("/")
        return needle in parts
    if pattern.startswith(".env."):
        return basename.startswith(".env.")
    return basename == pattern or name.endswith("/" + pattern) or pattern in name


def forbidden_entries(names: set[str], package_prefix: str) -> list[str]:
    patterns = [*FORBIDDEN_ANYWHERE, *FORBIDDEN_BY_PACKAGE.get(package_prefix, [])]
    found: list[str] = []
    for name in sorted(names):
        for pattern in patterns:
            if matches_forbidden(name, pattern):
                found.append(name)
                break
    return found


def verify_zip(path: Path, required: list[str], package_prefix: str) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        install_json = next((name for name in names if name.endswith("/INSTALL.json")), None)
        install_payload = None
        install_error = None
        if install_json:
            try:
                install_payload = json.loads(archive.read(install_json).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                install_error = str(exc)
    missing = [item for item in required if item not in names]
    forbidden = forbidden_entries(names, package_prefix)
    errors = []
    if install_error:
        errors.append(f"invalid INSTALL.json: {install_error}")
    if install_payload is not None:
        for key in ("package", "version", "client", "entrypoint", "quickstart"):
            if key not in install_payload:
                errors.append(f"INSTALL.json missing {key}")
    if forbidden:
        errors.append("forbidden files found")
    return {
        "package": path.name,
        "ok": not missing and not errors,
        "missing": missing,
        "forbidden": forbidden,
        "errors": errors,
    }


def run_self_check() -> int:
    with tempfile.TemporaryDirectory(prefix="release-package-verify-") as tmp:
        root = Path(tmp)
        package = root / "codex-multi-agent-skill-v0.0.0.zip"
        with zipfile.ZipFile(package, "w") as archive:
            for item in REQUIRED_BY_PACKAGE["codex-multi-agent-skill"]:
                if item.endswith("/INSTALL.json"):
                    archive.writestr(
                        item,
                        json.dumps(
                            {
                                "package": "codex-multi-agent",
                                "version": "0.0.0",
                                "client": "codex",
                                "entrypoint": "SKILL.md",
                                "quickstart": "QUICKSTART.md",
                            }
                        ),
                    )
                else:
                    archive.writestr(item, "")
        result = verify_zip(package, REQUIRED_BY_PACKAGE["codex-multi-agent-skill"], "codex-multi-agent-skill")
        if not result["ok"]:
            print(json.dumps({"ok": False, "result": result}, indent=2))
            return 1
    print(json.dumps({"ok": True, "message": "release package verifier self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Version suffix without leading v; default: newest matching zip")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    results = []
    errors = []
    for prefix, required in REQUIRED_BY_PACKAGE.items():
        package = find_package(prefix, args.version)
        if not package:
            result = {"package": f"{prefix}-v{args.version or '*'}", "ok": False, "missing": ["package zip not found"]}
        else:
            result = verify_zip(package, required, prefix)
        results.append(result)
        if not result["ok"]:
            errors.append(result)

    payload = {"ok": not errors, "results": results, "errors": errors}
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
