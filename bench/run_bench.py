#!/usr/bin/env python3
"""Local SWE-style benchmark harness (dependency-free, mock-ok dry runtime)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_OPENCLAW_SCRIPTS = REPO_ROOT / "adapters" / "openclaw" / "scripts"
if str(_OPENCLAW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_OPENCLAW_SCRIPTS))
from _runtimes import BENCH_RUNTIME_CHOICES  # noqa: E402
BENCH_ROOT = REPO_ROOT / "bench"
CASES_DIR = BENCH_ROOT / "cases"
CREATE_TASK_CARDS = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "create_task_cards.py"
UPDATE_STATUS = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "update_task_status.py"
AUDIT = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "audit_worker_output.py"
RUN_MULTI = REPO_ROOT / "scripts" / "run_multi_agent.py"

FIXES = {
    "fix-add": [(r"return a \+ b - 1", "return a + b")],
    "fix-reverse": [(r"return value", "return value[::-1]")],
    "fix-fib": [(r"return 1  # BUG: fib\(0\) should be 0", "return n")],
}


def run_cmd(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, capture_output=True, text=True, check=False)


def has_pytest() -> bool:
    return importlib.util.find_spec("pytest") is not None


def run_stdlib_tests(workspace: Path) -> tuple[bool, str]:
    runner = r"""
import importlib.util
import traceback
from pathlib import Path

failures = []
for path in sorted(Path("tests").glob("test_*.py")):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        for name in sorted(dir(module)):
            if name.startswith("test_") and callable(getattr(module, name)):
                try:
                    getattr(module, name)()
                except Exception:
                    failures.append(f"{path}:{name}\n{traceback.format_exc()}")
    except Exception:
        failures.append(f"{path}:module\n{traceback.format_exc()}")
if failures:
    print("\n\n".join(failures))
    raise SystemExit(1)
print("stdlib test runner passed")
"""
    env = {**os.environ, "PYTHONPATH": str(workspace)}
    proc = run_cmd([sys.executable, "-c", runner], cwd=workspace, env=env)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def discover_cases() -> list[Path]:
    return sorted(path for path in CASES_DIR.iterdir() if path.is_dir() and (path / "README.md").exists())


def setup_workspace(case_dir: Path, tmp_root: Path) -> Path:
    workspace = tmp_root / case_dir.name
    shutil.copytree(case_dir, workspace)
    return workspace


def generate_task_cards(workspace: Path, case_name: str) -> Path:
    state_dir = workspace / ".codex-multi-agent"
    yaml_path = workspace / "bench-task.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                f'task: "Bench case {case_name}"',
                "mode: fix",
                "runtime: native",
                "reviewers: []",
                "modules:",
                "  - name: src",
                "    paths:",
                "      - src/**",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc = run_cmd(
        [
            sys.executable,
            str(CREATE_TASK_CARDS),
            "--from-yaml",
            str(yaml_path),
            "--out",
            str(state_dir),
            "--workspace-root",
            str(workspace),
            "--runtime",
            "native",
        ],
        cwd=REPO_ROOT,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"create_task_cards failed: {proc.stderr or proc.stdout}")
    return state_dir


def worker_task_card(state_dir: Path) -> Path | None:
    tasks = state_dir / "tasks"
    for card in sorted(tasks.glob("T*-worker-*.md")):
        return card
    for card in sorted(tasks.glob("*.md")):
        if "worker" in card.name:
            return card
    return None


def apply_fix(case_name: str, workspace: Path) -> list[str]:
    changed: list[str] = []
    for rel_path in workspace.rglob("*.py"):
        if "tests" in rel_path.parts:
            continue
        text = rel_path.read_text(encoding="utf-8")
        original = text
        for pattern, replacement in FIXES.get(case_name, []):
            text = re.sub(pattern, replacement, text)
        if text != original:
            rel_path.write_text(text, encoding="utf-8")
            changed.append(str(rel_path.relative_to(workspace)).replace("\\", "/"))
    return changed


def write_worker_result(state_dir: Path, card_path: Path, workspace: Path, files_changed: list[str]) -> None:
    card_text = card_path.read_text(encoding="utf-8")
    task_id = re.search(r"^task_id:\s*(\S+)", card_text, re.MULTILINE)
    session = re.search(r"^session_name:\s*(\S+)", card_text, re.MULTILINE)
    tid = task_id.group(1) if task_id else "T002"
    sess = session.group(1) if session else "worker-src"
    result = {
        "task_id": tid,
        "session_name": sess,
        "role": "Worker",
        "status": "completed",
        "summary": "Dry-runtime worker applied deterministic fix",
        "workspace_observed": str(workspace),
        "required_paths_verified": True,
        "required_paths_missing": [],
        "files_read": files_changed,
        "tools_used": ["repo_index_tool", "test_runner_tool", "git_tool"],
        "files_changed": files_changed,
    }
    results_dir = state_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    json_path = results_dir / f"{tid}-{sess}.json"
    md_path = results_dir / f"{tid}-{sess}.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                f"task_id: {tid}",
                f"session_name: {sess}",
                "role: Worker",
                "status: completed",
                f"summary: {result['summary']}",
                "tools_used:",
                *[f"  - {item}" for item in result["tools_used"]],
                "files_changed:",
                *[f"  - {item}" for item in files_changed],
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def run_tests(workspace: Path) -> tuple[bool, str]:
    if not has_pytest():
        return run_stdlib_tests(workspace)
    env = {**os.environ, "PYTHONPATH": str(workspace)}
    proc = run_cmd([sys.executable, "-m", "pytest", "tests", "-q"], cwd=workspace, env=env)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def run_case(case_dir: Path, runtime: str, tmp_root: Path) -> dict:
    workspace = setup_workspace(case_dir, tmp_root)
    state_dir = generate_task_cards(workspace, case_dir.name)
    card = worker_task_card(state_dir)
    if not card:
        return {"case": case_dir.name, "ok": False, "error": "worker task card not found"}

    if runtime == "dry-runtime":
        files_changed = apply_fix(case_dir.name, workspace)
        if not files_changed:
            return {"case": case_dir.name, "ok": False, "error": "dry-runtime fix did not modify files"}
        write_worker_result(state_dir, card, workspace, files_changed)
    else:
        proc = run_cmd(
            [sys.executable, str(RUN_MULTI), "--runtime", runtime, "--task-card", str(card), "--state-dir", str(state_dir)],
            cwd=REPO_ROOT,
        )
        if proc.returncode != 0:
            return {
                "case": case_dir.name,
                "ok": False,
                "error": "launcher failed",
                "output": (proc.stdout or proc.stderr)[-500:],
            }

    worker_json = next(state_dir.glob("results/T*-worker-*.json"), None)
    if worker_json:
        data = json.loads(worker_json.read_text(encoding="utf-8"))
        changed = data.get("files_changed") or []
        (state_dir / "changed-files.txt").write_text("\n".join(changed) + ("\n" if changed else ""), encoding="utf-8")

    sync = run_cmd([sys.executable, str(UPDATE_STATUS), "--state-dir", str(state_dir), "--sync"], cwd=REPO_ROOT)
    if sync.returncode != 0:
        return {"case": case_dir.name, "ok": False, "error": "sync failed", "output": sync.stderr}

    audit = run_cmd(
        [
            sys.executable,
            str(AUDIT),
            "--ownership",
            str(state_dir / "ownership.json"),
            "--results",
            str(state_dir / "results"),
            "--changed-files",
            str(state_dir / "changed-files.txt"),
            "--write-audit",
            "--state-dir",
            str(state_dir),
        ],
        cwd=REPO_ROOT,
    )
    summarize = run_cmd([sys.executable, str(UPDATE_STATUS), "--state-dir", str(state_dir), "--summarize"], cwd=REPO_ROOT)
    tests_ok, test_output = run_tests(workspace)

    audit_payload = {}
    if audit.stdout.strip():
        try:
            audit_payload = json.loads(audit.stdout)
        except json.JSONDecodeError:
            audit_payload = {"raw": audit.stdout[:200]}

    return {
        "case": case_dir.name,
        "ok": tests_ok and audit_payload.get("ok", False),
        "tests_ok": tests_ok,
        "audit_ok": audit_payload.get("ok"),
        "test_output": test_output[-400:],
        "state_dir": str(state_dir),
    }


def run_self_check(dry_runtime: str = "dry-runtime") -> int:
    errors: list[str] = []
    cases = discover_cases()
    if len(cases) < 2:
        errors.append("expected >= 2 bench cases")

    with tempfile.TemporaryDirectory(prefix="bench-selfcheck-") as tmp:
        results = [run_case(case, dry_runtime, Path(tmp)) for case in cases]
        for item in results:
            if not item.get("ok"):
                errors.append(f"{item.get('case')}: {item.get('error') or item}")

    claude_fixture = run_cmd(
        [
            sys.executable,
            str(REPO_ROOT / "adapters" / "claude-code" / "scripts" / "dogfood_claude.py"),
            "--fixture-log",
            str(REPO_ROOT / "adapters" / "_shared" / "fixtures" / "claude_429_budget.log"),
        ]
    )
    if claude_fixture.returncode != 0:
        errors.append("dogfood_claude fixture self-check failed")
    else:
        payload = json.loads(claude_fixture.stdout)
        if payload.get("status") != "skipped":
            errors.append("dogfood_claude fixture must report skipped not ok")

    if errors:
        print(json.dumps({"ok": False, "errors": errors, "results": results}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "bench self-check passed", "cases": [r["case"] for r in results]}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime",
        default="codex",
        choices=list(BENCH_RUNTIME_CHOICES),
        help="Bench launcher runtime",
    )
    parser.add_argument("--case", help="Run a single case directory name")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--dry-runtime", action="store_true", help="Alias for --runtime dry-runtime with --self-check")
    args = parser.parse_args()

    runtime = "dry-runtime" if args.dry_runtime else args.runtime
    if args.self_check or args.dry_runtime:
        return run_self_check(runtime)

    cases = discover_cases()
    if args.case:
        cases = [c for c in cases if c.name == args.case]
        if not cases:
            print(json.dumps({"ok": False, "error": f"case not found: {args.case}"}))
            return 1

    with tempfile.TemporaryDirectory(prefix="bench-run-") as tmp:
        results = [run_case(case, runtime, Path(tmp)) for case in cases]
    ok = all(item.get("ok") for item in results)
    print(json.dumps({"ok": ok, "runtime": runtime, "results": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
