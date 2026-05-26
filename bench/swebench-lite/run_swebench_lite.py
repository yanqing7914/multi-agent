#!/usr/bin/env python3
"""SWE-bench Lite-style offline benchmark harness (dependency-free)."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_OPENCLAW_SCRIPTS = REPO_ROOT / "adapters" / "openclaw" / "scripts"
if str(_OPENCLAW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_OPENCLAW_SCRIPTS))
from _runtimes import BENCH_RUNTIME_CHOICES  # noqa: E402
BENCH_ROOT = Path(__file__).resolve().parent
CASES_DIR = BENCH_ROOT / "cases"
RESULTS_ROOT = BENCH_ROOT / "results"
CREATE_TASK_CARDS = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "create_task_cards.py"
UPDATE_STATUS = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "update_task_status.py"
AUDIT = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "audit_worker_output.py"
RUN_MULTI = REPO_ROOT / "scripts" / "run_multi_agent.py"


def run_cmd(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, capture_output=True, text=True, check=False)


def workspace_relative_paths(paths: list[str], workspace: Path) -> list[str]:
    normalized: list[str] = []
    workspace_resolved = workspace.resolve()
    for item in paths:
        value = str(item).replace("\\", "/").strip()
        if not value:
            continue
        try:
            candidate = Path(value)
            if candidate.is_absolute():
                value = str(candidate.resolve().relative_to(workspace_resolved)).replace("\\", "/")
        except (OSError, ValueError):
            pass
        while value.startswith("./"):
            value = value[2:]
        normalized.append(value)
    return list(dict.fromkeys(normalized))


def discover_cases() -> list[Path]:
    cases: list[Path] = []
    if not CASES_DIR.is_dir():
        return cases
    for path in sorted(CASES_DIR.iterdir()):
        if not path.is_dir():
            continue
        if (path / "repo").is_dir() and (path / "tests").is_dir() and (path / "golden_patch.diff").is_file():
            cases.append(path)
    return cases


def apply_unified_diff(case_dir: Path, workspace: Path, diff_text: str) -> list[str]:
    """Apply a unified diff rooted at case_dir to workspace (stdlib-only)."""
    changed: list[str] = []
    current_file: Path | None = None
    old_lines: list[str] = []
    new_lines: list[str] = []
    hunks: list[tuple[Path, list[str], list[str]]] = []

    def flush() -> None:
        nonlocal current_file, old_lines, new_lines
        if current_file is not None:
            hunks.append((current_file, old_lines, new_lines))
        current_file = None
        old_lines = []
        new_lines = []

    for raw in diff_text.splitlines():
        if raw.startswith("+++ b/"):
            flush()
            rel = raw[len("+++ b/") :].strip()
            current_file = workspace / rel
            continue
        if raw.startswith("--- a/"):
            continue
        if raw.startswith("@@"):
            continue
        if current_file is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            new_lines.append(raw[1:])
        elif raw.startswith("-") and not raw.startswith("---"):
            old_lines.append(raw[1:])
        elif raw.startswith(" "):
            line = raw[1:]
            old_lines.append(line)
            new_lines.append(line)

    flush()

    for target, old, new in hunks:
        if not target.exists():
            raise FileNotFoundError(f"patch target missing: {target}")
        content = target.read_text(encoding="utf-8").splitlines(keepends=True)
        old_text = "".join(f"{line}\n" for line in old)
        new_text = "".join(f"{line}\n" for line in new)
        joined = "".join(content)
        if old_text not in joined:
            raise ValueError(f"patch context not found in {target}")
        target.write_text(joined.replace(old_text, new_text, 1), encoding="utf-8")
        try:
            rel = target.relative_to(workspace)
            changed.append(str(rel).replace("\\", "/"))
        except ValueError:
            changed.append(str(target))
    return list(dict.fromkeys(changed))


def apply_golden_patch(case_dir: Path, workspace: Path) -> list[str]:
    diff_path = case_dir / "golden_patch.diff"
    return apply_unified_diff(case_dir, workspace, diff_path.read_text(encoding="utf-8"))


def setup_workspace(case_dir: Path, dest: Path) -> Path:
    workspace = dest / case_dir.name
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    shutil.copytree(case_dir / "repo", workspace / "repo")
    shutil.copytree(case_dir / "tests", workspace / "tests")
    for name in ("bug.md", "golden_patch.diff"):
        src = case_dir / name
        if src.exists():
            shutil.copy2(src, workspace / name)
    return workspace


def run_pytest(workspace: Path) -> tuple[bool, str, float]:
    env = {**os.environ, "PYTHONPATH": str(workspace / "repo")}
    proc = run_cmd([sys.executable, "-m", "pytest", "tests", "-q"], cwd=workspace, env=env)
    output = (proc.stdout or "") + (proc.stderr or "")
    passed = proc.returncode == 0
    pass_rate = 1.0 if passed else 0.0
    return passed, output.strip(), pass_rate


def generate_task_cards(workspace: Path, case_name: str) -> Path:
    state_dir = workspace / ".codex-multi-agent"
    yaml_path = workspace / "bench-task.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                f'task: "SWE-bench Lite case {case_name}"',
                "mode: fix",
                "runtime: native",
                "reviewers: []",
                "modules:",
                "  - name: repo",
                "    paths:",
                "      - repo/**",
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


def write_worker_result(state_dir: Path, card_path: Path, workspace: Path, files_changed: list[str]) -> None:
    card_text = card_path.read_text(encoding="utf-8")
    task_id = re.search(r"^task_id:\s*(\S+)", card_text, re.MULTILINE)
    session = re.search(r"^session_name:\s*(\S+)", card_text, re.MULTILINE)
    tid = task_id.group(1) if task_id else "T002"
    sess = session.group(1) if session else "worker-repo"
    result = {
        "task_id": tid,
        "session_name": sess,
        "role": "Worker",
        "status": "completed",
        "summary": "Applied golden_patch.diff (self-check worker simulation)",
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


def write_case_artifacts(case_name: str, workspace: Path, state_dir: Path, score: dict) -> Path:
    out_dir = RESULTS_ROOT / case_name
    for sub in ("cards", "results", "summary", "audit"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    tasks_src = state_dir / "tasks"
    if tasks_src.is_dir():
        for card in tasks_src.glob("*.md"):
            shutil.copy2(card, out_dir / "cards" / card.name)

    results_src = state_dir / "results"
    if results_src.is_dir():
        for item in results_src.iterdir():
            if item.is_file():
                shutil.copy2(item, out_dir / "results" / item.name)

    summary_src = state_dir / "summary" / "run-summary.md"
    if summary_src.exists():
        shutil.copy2(summary_src, out_dir / "summary" / "run-summary.md")
    else:
        (out_dir / "summary" / "run-summary.md").write_text(
            f"# {case_name}\n\npytest pass-rate: {score.get('pass_rate')}\n",
            encoding="utf-8",
        )

    audits_src = state_dir / "audits"
    if audits_src.is_dir():
        for item in audits_src.glob("*.json"):
            shutil.copy2(item, out_dir / "audit" / item.name)

    (out_dir / "score.json").write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
    return out_dir


def run_case(case_dir: Path, runtime: str, tmp_root: Path, persist: bool = True) -> dict:
    case_name = case_dir.name
    workspace = setup_workspace(case_dir, tmp_root)

    pre_ok, pre_output, pre_rate = run_pytest(workspace)
    if pre_ok:
        return {
            "case": case_name,
            "ok": False,
            "error": "expected failing tests before patch",
            "pre_test_output": pre_output[-400:],
        }

    state_dir = generate_task_cards(workspace, case_name)
    card = worker_task_card(state_dir)
    if not card:
        return {"case": case_name, "ok": False, "error": "worker task card not found"}

    files_changed: list[str] = []
    if runtime in {"dry", "dry-runtime"}:
        try:
            files_changed = apply_golden_patch(case_dir, workspace)
        except (OSError, ValueError) as exc:
            return {"case": case_name, "ok": False, "error": f"golden patch apply failed: {exc}"}
        if not files_changed:
            return {"case": case_name, "ok": False, "error": "golden patch did not modify files"}
        write_worker_result(state_dir, card, workspace, files_changed)
    else:
        runtime_arg = runtime
        if runtime == "claude":
            runtime_arg = "claude-code"
        proc = run_cmd(
            [
                sys.executable,
                str(RUN_MULTI),
                "--runtime",
                runtime_arg,
                "--task-card",
                str(card),
                "--state-dir",
                str(state_dir),
            ],
            cwd=REPO_ROOT,
        )
        if proc.returncode != 0:
            return {
                "case": case_name,
                "ok": False,
                "error": "launcher failed",
                "output": (proc.stdout or proc.stderr)[-500:],
            }

    post_ok, post_output, post_rate = run_pytest(workspace)

    worker_json = next(state_dir.glob("results/T*-worker-*.json"), None)
    if worker_json:
        data = json.loads(worker_json.read_text(encoding="utf-8"))
        changed = workspace_relative_paths(data.get("files_changed") or [], workspace)
        files_changed = changed
        if data.get("files_changed") != changed:
            data["files_changed"] = changed
            worker_json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        (state_dir / "changed-files.txt").write_text("\n".join(changed) + ("\n" if changed else ""), encoding="utf-8")

    sync = run_cmd([sys.executable, str(UPDATE_STATUS), "--state-dir", str(state_dir), "--sync"], cwd=REPO_ROOT)
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
    run_cmd([sys.executable, str(UPDATE_STATUS), "--state-dir", str(state_dir), "--summarize"], cwd=REPO_ROOT)

    audit_payload: dict = {}
    if audit.stdout.strip():
        try:
            audit_payload = json.loads(audit.stdout)
        except json.JSONDecodeError:
            audit_payload = {"raw": audit.stdout[:200]}

    score = {
        "case": case_name,
        "pre_pass_rate": pre_rate,
        "post_pass_rate": post_rate,
        "pytest_passed": post_ok,
        "tests_ok": post_ok,
        "audit_ok": audit_payload.get("ok"),
        "runtime": runtime,
        "files_changed": files_changed,
    }
    if persist:
        write_case_artifacts(case_name, workspace, state_dir, score)

    return {
        "case": case_name,
        "ok": post_ok and bool(audit_payload.get("ok")),
        "tests_ok": post_ok,
        "audit_ok": audit_payload.get("ok"),
        "pass_rate": post_rate,
        "pre_pass_rate": pre_rate,
        "test_output": post_output[-400:],
        "score_path": str(RESULTS_ROOT / case_name / "score.json") if persist else None,
        "state_dir": str(state_dir),
    }


def archive_score_snapshot(score: dict, *, no_archive: bool = False) -> Path | None:
    """Write score-YYYYMMDD-HHMMSS.json under bench/swebench-lite/results/ for trend tracking."""
    if no_archive:
        return None
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = RESULTS_ROOT / f"score-{stamp}.json"
    path.write_text(json.dumps(score, indent=2) + "\n", encoding="utf-8")
    return path


def aggregate_score(results: list[dict]) -> dict:
    rates = [item.get("pass_rate", 0.0) for item in results if "pass_rate" in item]
    aggregate = sum(rates) / len(rates) if rates else 0.0
    return {
        "cases": len(results),
        "passed": sum(1 for item in results if item.get("ok")),
        "aggregate_pass_rate": aggregate,
        "per_case": {item["case"]: item.get("pass_rate", 0.0) for item in results if "case" in item},
    }


def run_self_check(runtime: str = "dry") -> int:
    errors: list[str] = []
    cases = discover_cases()
    if len(cases) < 3:
        errors.append(f"expected >= 3 swebench-lite cases, found {len(cases)}")

    with tempfile.TemporaryDirectory(prefix="swebench-lite-selfcheck-") as tmp:
        results = [run_case(case, runtime, Path(tmp), persist=False) for case in cases]
        for item in results:
            if not item.get("ok"):
                errors.append(f"{item.get('case')}: {item.get('error') or item}")

        agg = aggregate_score(results)
        if agg["passed"] != len(cases):
            errors.append(f"aggregate pass mismatch: {agg}")

        # patch applier sanity on first case
        if cases:
            ws = setup_workspace(cases[0], Path(tmp) / "patch-check")
            try:
                changed = apply_golden_patch(cases[0], ws)
                if not changed:
                    errors.append("golden patch applier returned no files")
            except (OSError, ValueError) as exc:
                errors.append(f"golden patch applier failed: {exc}")

    if errors:
        print(json.dumps({"ok": False, "errors": errors, "results": results}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "message": "swebench-lite self-check passed",
                "cases": [r["case"] for r in results],
                "aggregate": aggregate_score(results),
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", default="dry", choices=list(BENCH_RUNTIME_CHOICES))
    parser.add_argument("--no-archive", action="store_true", help="Skip writing score-YYYYMMDD-HHMMSS.json under results/")
    parser.add_argument("--case", help="Run a single case directory name")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--no-persist", action="store_true", help="Skip writing bench/swebench-lite/results/")
    args = parser.parse_args()

    runtime = "dry" if args.runtime == "dry-runtime" else args.runtime
    if args.self_check:
        return run_self_check(runtime)

    cases = discover_cases()
    if args.case:
        cases = [c for c in cases if c.name == args.case]
        if not cases:
            print(json.dumps({"ok": False, "error": f"case not found: {args.case}"}))
            return 1

    with tempfile.TemporaryDirectory(prefix="swebench-lite-run-") as tmp:
        results = [run_case(case, runtime, Path(tmp), persist=not args.no_persist) for case in cases]

    agg = aggregate_score(results)
    (RESULTS_ROOT / "aggregate-score.json").write_text(json.dumps(agg, indent=2) + "\n", encoding="utf-8")
    archive_payload = {"runtime": runtime, "aggregate": agg, "results": results, "archived_at": datetime.now(timezone.utc).isoformat()}
    archived = archive_score_snapshot(archive_payload, no_archive=args.no_archive)
    ok = all(item.get("ok") for item in results)
    output = {"ok": ok, "runtime": runtime, "aggregate": agg, "results": results}
    if archived:
        output["score_archive"] = str(archived)
    print(json.dumps(output, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
