#!/usr/bin/env python3
"""Build installable skill/client packages for supported agent clients."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST = REPO_ROOT / "dist"

COMMON_GENERIC = [
    "BENCHMARKS.md",
    "CHANGELOG.md",
    "README.md",
    "SKILL.md",
    "agents",
    "checklists",
    "docs/agent-install.md",
    "docs/architecture.md",
    "docs/clients.md",
    "docs/mcp-format.md",
    "docs/product.md",
    "docs/roadmap.md",
    "docs/safety-rules.md",
    "examples/README.md",
    "examples/bugfix.md",
    "examples/end-to-end-agent-install",
    "examples/feature.md",
    "examples/review.md",
    "templates",
    "tools",
]

OPENCLAW_FILES = [
    "adapters/openclaw/QUICKSTART.md",
    "adapters/openclaw/README.md",
    "adapters/openclaw/SKILL.md",
    "adapters/openclaw/examples",
    "adapters/openclaw/scripts",
    "adapters/openclaw/templates",
    # Task cards reference tools/worktree_tool.py for Worker isolation; ship it.
    "tools",
]

CLIENT_SHARED = [
    "adapters/_shared",
    "adapters/openclaw/QUICKSTART.md",
    "adapters/openclaw/README.md",
    "adapters/openclaw/scripts",
    "adapters/openclaw/templates",
    "checklists",
    "docs/agent-install.md",
    "scripts/install_native_skills.py",
    "scripts/run_multi_agent.py",
    "scripts/doctor.py",
    "templates",
    "tools",
]

CLIENTS = {
    "codex": {
        "root": "codex-multi-agent",
        "zip": "codex-multi-agent-skill",
        "adapter": "adapters/codex",
        "extra": ["adapters/codex/agents", "adapters/codex/scripts/doctor_codex.py"],
    },
    "cursor": {
        "root": "cursor-multi-agent",
        "zip": "cursor-multi-agent-pack",
        "adapter": "adapters/cursor",
        "extra": [],
    },
    "claude-code": {
        "root": "claude-code-multi-agent",
        "zip": "claude-code-multi-agent-pack",
        "adapter": "adapters/claude-code",
        "extra": ["adapters/claude-code/agents"],
    },
    "hermes": {
        "root": "hermes-multi-agent",
        "zip": "hermes-multi-agent-pack",
        "adapter": "adapters/hermes",
        "extra": [],
    },
}


def copy_path(src_rel: str, dest_root: Path, dest_rel: str | None = None) -> None:
    src = REPO_ROOT / src_rel
    dest = dest_root / (dest_rel or src_rel)
    if src.is_dir():
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def zip_dir(source: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(source.rglob("*")):
            if file.is_dir() or "__pycache__" in file.parts or file.suffix == ".pyc":
                continue
            info = zipfile.ZipInfo(file.relative_to(source.parent).as_posix())
            info.date_time = (2026, 1, 1, 0, 0, 0)
            mode = 0o755 if file.suffix == ".sh" else 0o644
            info.external_attr = mode << 16
            archive.writestr(info, file.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_generic(stage: Path, version: str) -> Path:
    root = stage / "multi-agent-coding"
    for item in COMMON_GENERIC:
        copy_path(item, root, item)
    zip_path = DIST / f"multi-agent-coding-skill-v{version}.zip"
    zip_dir(root, zip_path)
    return zip_path


def build_openclaw(stage: Path, version: str) -> Path:
    root = stage / "openclaw-multi-agent"
    for item in OPENCLAW_FILES:
        copy_path(item, root, item.replace("adapters/openclaw/", ""))
    zip_path = DIST / f"openclaw-multi-agent-skill-v{version}.zip"
    zip_dir(root, zip_path)
    return zip_path


def cursor_rules() -> str:
    return """# Cursor Rules: multi-agent-coding

Use this project as a multi-agent mission-control pack.

- Read `SKILL.md` first for trigger rules and role boundaries.
- Use `QUICKSTART.md` for the Golden Path.
- Generate task cards with `adapters/openclaw/scripts/create_task_cards.py`.
- Cursor App and Cursor CLI both discover this native skill from `.agents/skills`, `.cursor/skills`, or user skill directories.
- Primary path (App): the Main agent dispatches each Worker/Reviewer by spawning a Cursor subagent directly (in-App delegation) with the task-card prompt + `allowed_paths`; no external CLI needed.
- Optional scripted/CI path: the `agent` CLI bridge via `scripts/run_multi_agent.py --runtime cursor` (needs `agent` + tmux). `/multitask` (Cursor 3) is a user-driven alternative.
- Use `--runtime cursor-desktop` only when neither delegation nor the `agent` CLI is available (manual prompt handoff).
- Keep `.codex-multi-agent/` local unless the user explicitly asks to commit it.
- Workers may edit only `allowed_paths`; Reviewers stay read-only.
- Main must run gate sync and scope audit before final delivery.
"""


def claude_md() -> str:
    return """# Claude Code Project Instructions: multi-agent-coding

Use this pack for scoped multi-agent coding tasks.

- Read `SKILL.md` before coordinating roles.
- Claude Code App/IDE and Claude Code CLI both discover this native skill from `.claude/skills` or user skill directories.
- Install bundled subagents from `adapters/claude-code/agents` into `.claude/agents` or `~/.claude/agents`.
- For automatic local workers, use native subagents or `scripts/run_multi_agent.py --runtime claude-code`.
- Use `--runtime claude-desktop` only when the user explicitly wants a manual prompt handoff.
- Inside OpenClaw/Her, prefer ACP handoff with `adapters/claude-code/scripts/launch_claude_worker.sh --mode acp`.
- Generate task cards with `adapters/openclaw/scripts/create_task_cards.py`.
- Workers must write JSON and Markdown result reports before completion.
- Reviewers are read-only and may use review skills such as `ssrd` only when authorized.
- Main owns diff audit, validation, and final delivery.
"""


def build_client(stage: Path, version: str, client: str) -> Path:
    config = CLIENTS[client]
    root = stage / config["root"]

    copy_path(config["adapter"] + "/SKILL.md", root, "SKILL.md")
    copy_path(config["adapter"] + "/README.md", root, "README.md")
    copy_path(config["adapter"] + "/QUICKSTART.md", root, "QUICKSTART.md")
    native_contract = REPO_ROOT / config["adapter"] / "NATIVE_SUBAGENT_CONTRACT.md"
    if native_contract.exists():
        copy_path(config["adapter"] + "/NATIVE_SUBAGENT_CONTRACT.md", root, "NATIVE_SUBAGENT_CONTRACT.md")
    copy_path(config["adapter"], root, config["adapter"])
    for item in CLIENT_SHARED + config["extra"]:
        copy_path(item, root, item)

    if client == "cursor":
        write_text(root / "cursor-rules.md", cursor_rules())
        write_text(root / ".cursor" / "rules" / "multi-agent-coding.mdc", cursor_rules())
    if client == "claude-code":
        write_text(root / "CLAUDE.md", claude_md())
    if client == "codex":
        write_text(
            root / "agents" / "openai.yaml",
            """interface:
  display_name: "Codex Multi-Agent"
  short_description: "Use native Codex Desktop subagents, with handoff or CLI workers as fallbacks."
  brand_color: "#2563EB"
  default_prompt: "Use $codex-multi-agent to coordinate this coding task with native Codex Desktop subagents, scoped paths, review, verification, and audit."
policy:
  allow_implicit_invocation: true
""",
        )

    write_text(
        root / "INSTALL.json",
        json.dumps(
            {
                "package": config["root"],
                "version": version,
                "client": client,
                "entrypoint": "SKILL.md",
                "quickstart": "QUICKSTART.md",
            },
            indent=2,
        )
        + "\n",
    )
    zip_path = DIST / f"{config['zip']}-v{version}.zip"
    zip_dir(root, zip_path)
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    DIST.mkdir(exist_ok=True)
    stage = DIST / ".package-stage"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()

    zips = [
        build_generic(stage, args.version),
        build_openclaw(stage, args.version),
        *(build_client(stage, args.version, client) for client in CLIENTS),
    ]
    shutil.rmtree(stage)

    payload = {
        "ok": True,
        "version": args.version,
        "packages": [
            {"name": path.name, "size": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(zips)
        ],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
