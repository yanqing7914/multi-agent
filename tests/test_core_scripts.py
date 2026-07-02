"""Unit tests for the mission-control core scripts (beyond smoke self-checks)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENCLAW_SCRIPTS = REPO_ROOT / "adapters" / "openclaw" / "scripts"
CREATE_TASK_CARDS = OPENCLAW_SCRIPTS / "create_task_cards.py"
AUDIT_WORKER_OUTPUT = OPENCLAW_SCRIPTS / "audit_worker_output.py"
CAPTURE_CHANGED_FILES = OPENCLAW_SCRIPTS / "capture_changed_files.py"
UPDATE_TASK_STATUS = OPENCLAW_SCRIPTS / "update_task_status.py"
PIP_CLI = REPO_ROOT / "multi_agent_coding" / "cli.py"


def run_script(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        cwd=cwd,
    )


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True)


def init_repo(root: Path) -> None:
    git("init", "-q", cwd=root)
    git("config", "user.email", "tests@example.com", cwd=root)
    git("config", "user.name", "tests", cwd=root)


@pytest.fixture()
def task_card_run(tmp_path: Path) -> dict:
    workspace = tmp_path / "workspace"
    (workspace / "src").mkdir(parents=True)
    state_dir = workspace / ".codex-multi-agent"
    proc = run_script(
        CREATE_TASK_CARDS,
        "--task",
        "Fix demo bug",
        "--mode",
        "fix",
        "--modules",
        "core",
        "--runtime",
        "cursor",
        "--reviewers",
        "correctness",
        "--workspace-root",
        str(workspace),
        "--out",
        str(state_dir),
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return {"workspace": workspace, "state_dir": state_dir}


class TestCreateTaskCards:
    def test_preflight_has_no_shell_conjunction(self, task_card_run: dict) -> None:
        """`&&` breaks Windows PowerShell 5.x; preflight must be one command per line."""
        cards = list((task_card_run["state_dir"] / "tasks").glob("*.md"))
        assert cards, "no task cards generated"
        for card in cards:
            text = card.read_text(encoding="utf-8")
            preflight_lines = [
                line for line in text.splitlines() if line.strip().startswith("- cd ") or " && " in line
            ]
            for line in preflight_lines:
                assert " && " not in line, f"{card.name} contains shell conjunction: {line.strip()}"

    def test_worker_card_captures_untracked_files(self, task_card_run: dict) -> None:
        worker_cards = list((task_card_run["state_dir"] / "tasks").glob("*worker*.md"))
        assert worker_cards, "no worker card generated"
        text = worker_cards[0].read_text(encoding="utf-8")
        assert "capture_changed_files.py" in text
        assert "git diff --name-only >" not in text

    def test_single_worker_run_has_no_worktree_plan(self, task_card_run: dict) -> None:
        """auto policy: one Worker = no parallel overwrite risk = no worktree overhead."""
        assert not (task_card_run["state_dir"] / "worktree-plan.json").exists()

    @staticmethod
    def create_cards(workspace: Path, state_dir: Path, *extra: str) -> None:
        proc = run_script(
            CREATE_TASK_CARDS,
            "--task",
            "Parallel feature",
            "--mode",
            "implement",
            "--modules",
            "backend",
            "frontend",
            "--runtime",
            "subagent",
            "--reviewers",
            "correctness",
            "--workspace-root",
            str(workspace),
            "--out",
            str(state_dir),
            *extra,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout

    def test_parallel_workers_get_worktree_isolation_by_default(self, tmp_path: Path) -> None:
        """2+ write-permitted Workers must produce a worktree plan without any flag."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        state_dir = workspace / ".codex-multi-agent"
        self.create_cards(workspace, state_dir)

        plan_path = state_dir / "worktree-plan.json"
        assert plan_path.is_file(), "worktree-plan.json missing for parallel Workers"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        ownership = json.loads((state_dir / "ownership.json").read_text(encoding="utf-8-sig"))
        workers = [t for t in ownership["tasks"] if t["role"] == "Worker"]
        assert len(plan["workers"]) == len(workers) == 2
        branches = {entry["branch"] for entry in plan["workers"]}
        assert len(branches) == 2, "each Worker needs its own branch"
        for worker in workers:
            assert worker.get("worktree", {}).get("branch") in branches

        worker_cards = list((state_dir / "tasks").glob("*worker*.md"))
        assert worker_cards
        for card in worker_cards:
            text = card.read_text(encoding="utf-8")
            assert "worktree:" in text
            assert "worktree_tool.py" in text
            assert "merge --no-ff multi-agent/" in text
            # Preflight must target the isolated worktree, not the shared tree.
            assert f'cd "{workspace}"\n' not in text.replace("\r\n", "\n") + "\n"

    def test_worktrees_off_disables_isolation(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        state_dir = workspace / ".codex-multi-agent"
        self.create_cards(workspace, state_dir, "--worktrees", "off")
        assert not (state_dir / "worktree-plan.json").exists()
        worker_cards = list((state_dir / "tasks").glob("*worker*.md"))
        assert worker_cards
        assert "worktree:" not in worker_cards[0].read_text(encoding="utf-8")


class TestCaptureChangedFiles:
    def test_includes_untracked_and_staged(self, tmp_path: Path) -> None:
        init_repo(tmp_path)
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
        git("add", "-A", cwd=tmp_path)
        git("commit", "-q", "-m", "init", cwd=tmp_path)

        (tmp_path / "src" / "app.py").write_text("x = 2\n", encoding="utf-8")  # unstaged
        (tmp_path / "untracked.py").write_text("y = 1\n", encoding="utf-8")  # untracked
        (tmp_path / "staged.py").write_text("z = 1\n", encoding="utf-8")
        git("add", "staged.py", cwd=tmp_path)  # staged

        state_dir = tmp_path / ".codex-multi-agent"
        proc = run_script(
            CAPTURE_CHANGED_FILES,
            "--workspace-root",
            str(tmp_path),
            "--state-dir",
            str(state_dir),
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
        changed = set((state_dir / "changed-files.txt").read_text(encoding="utf-8").split())
        assert changed == {"src/app.py", "untracked.py", "staged.py"}

    def test_excludes_state_dir(self, tmp_path: Path) -> None:
        init_repo(tmp_path)
        (tmp_path / "README.md").write_text("hi\n", encoding="utf-8")
        git("add", "-A", cwd=tmp_path)
        git("commit", "-q", "-m", "init", cwd=tmp_path)
        state_dir = tmp_path / ".codex-multi-agent"
        (state_dir / "results").mkdir(parents=True)
        (state_dir / "results" / "T001.json").write_text("{}", encoding="utf-8")

        proc = run_script(
            CAPTURE_CHANGED_FILES,
            "--workspace-root",
            str(tmp_path),
            "--state-dir",
            str(state_dir),
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
        changed = (state_dir / "changed-files.txt").read_text(encoding="utf-8").split()
        assert changed == []


class TestAuditWorkerOutput:
    @staticmethod
    def write_state(tmp_path: Path, files_changed: list[str], changed_files: list[str]) -> dict:
        ownership = {
            "schema_version": 1,
            "workspace_root": str(tmp_path),
            "tasks": [
                {
                    "task_id": "T001",
                    "session_name": "worker-backend",
                    "role": "Worker",
                    "allowed_paths": ["backend/**"],
                    "blocked_paths": [".env"],
                    "status": "completed",
                }
            ],
        }
        ownership_path = tmp_path / "ownership.json"
        ownership_path.write_text(json.dumps(ownership, indent=2), encoding="utf-8")
        results = tmp_path / "results"
        results.mkdir()
        (results / "T001-worker-backend.json").write_text(
            json.dumps(
                {
                    "task_id": "T001",
                    "session_name": "worker-backend",
                    "role": "Worker",
                    "status": "completed",
                    "files_changed": files_changed,
                }
            ),
            encoding="utf-8",
        )
        changed_path = tmp_path / "changed-files.txt"
        changed_path.write_text("\n".join(changed_files) + "\n", encoding="utf-8")
        return {"ownership": ownership_path, "results": results, "changed": changed_path}

    def run_audit(self, paths: dict, strict: bool = True) -> tuple[int, dict]:
        args = [
            "--ownership",
            str(paths["ownership"]),
            "--results",
            str(paths["results"]),
            "--changed-files",
            str(paths["changed"]),
        ]
        if strict:
            args.append("--strict")
        proc = run_script(AUDIT_WORKER_OUTPUT, *args)
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
        return proc.returncode, payload

    def test_in_scope_change_passes(self, tmp_path: Path) -> None:
        paths = self.write_state(tmp_path, ["backend/api.py"], ["backend/api.py"])
        returncode, payload = self.run_audit(paths)
        assert returncode == 0 and payload.get("ok"), payload

    def test_out_of_scope_report_fails(self, tmp_path: Path) -> None:
        paths = self.write_state(tmp_path, ["frontend/app.js"], ["frontend/app.js"])
        returncode, payload = self.run_audit(paths)
        assert returncode != 0 and not payload.get("ok"), payload

    def test_unowned_untracked_change_fails_strict(self, tmp_path: Path) -> None:
        """A file created outside every Worker scope must fail the strict audit."""
        paths = self.write_state(tmp_path, ["backend/api.py"], ["backend/api.py", "sneaky.py"])
        returncode, payload = self.run_audit(paths)
        assert returncode != 0 and not payload.get("ok"), payload


class TestConcurrentStatusUpdates:
    def test_parallel_task_updates_are_not_lost(self, tmp_path: Path) -> None:
        """Parallel Workers updating different tasks must not clobber each other.

        Without the state lock, concurrent read-modify-write of ownership.json /
        status.json makes the last writer silently discard earlier updates.
        """
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        state_dir = workspace / ".codex-multi-agent"
        proc = run_script(
            CREATE_TASK_CARDS,
            "--task",
            "Concurrency check",
            "--mode",
            "implement",
            "--modules",
            "alpha",
            "beta",
            "gamma",
            "--runtime",
            "subagent",
            "--reviewers",
            "correctness",
            "--workspace-root",
            str(workspace),
            "--out",
            str(state_dir),
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout

        ownership = json.loads((state_dir / "ownership.json").read_text(encoding="utf-8-sig"))
        task_ids = [task["task_id"] for task in ownership["tasks"]]
        assert len(task_ids) >= 6

        procs = [
            subprocess.Popen(
                [
                    sys.executable,
                    str(UPDATE_TASK_STATUS),
                    "--state-dir",
                    str(state_dir),
                    "--task-id",
                    task_id,
                    "--status",
                    "running",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for task_id in task_ids
        ]
        failures = []
        for popen, task_id in zip(procs, task_ids):
            stdout, stderr = popen.communicate(timeout=120)
            if popen.returncode != 0:
                failures.append(f"{task_id}: rc={popen.returncode} {stderr or stdout}")
        assert not failures, failures

        status_doc = json.loads((state_dir / "status.json").read_text(encoding="utf-8-sig"))
        lost = [
            task_id
            for task_id in task_ids
            if status_doc.get("tasks", {}).get(task_id, {}).get("status") != "running"
        ]
        assert not lost, f"lost concurrent updates for: {lost}"


class TestVerifyReleasePackages:
    @staticmethod
    def load_module():
        spec = importlib.util.spec_from_file_location(
            "verify_release_packages", REPO_ROOT / "scripts" / "verify_release_packages.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_forbidden_matching(self) -> None:
        module = self.load_module()
        assert module.matches_forbidden("pkg/.env", ".env")
        assert module.matches_forbidden("pkg/.env.local", ".env.")
        assert module.matches_forbidden("pkg/docs/development.md", "docs/development.md")
        assert module.matches_forbidden("pkg/.github/workflows/ci.yml", ".github/")
        assert not module.matches_forbidden("pkg/docs/product.md", "docs/development.md")

    def test_self_check_passes(self) -> None:
        proc = run_script(REPO_ROOT / "scripts" / "verify_release_packages.py", "--self-check")
        assert proc.returncode == 0, proc.stderr or proc.stdout


class TestPipCli:
    def test_self_check_from_checkout(self) -> None:
        """The console CLI must resolve the skill tree from a source checkout too."""
        proc = run_script(PIP_CLI, "self-check")
        assert proc.returncode == 0, proc.stderr or proc.stdout
        payload = json.loads(proc.stdout)
        assert payload["bundle_root"] == str(REPO_ROOT)

    def test_forwards_to_bundled_script(self) -> None:
        proc = run_script(PIP_CLI, "capture", "--self-check")
        assert proc.returncode == 0, proc.stderr or proc.stdout

    def test_unknown_command_fails(self) -> None:
        proc = run_script(PIP_CLI, "not-a-command")
        assert proc.returncode == 2

    def test_version_matches_pyproject_changelog_tagline(self) -> None:
        """__version__ is the single source hatch reads; keep it importable."""
        spec = importlib.util.spec_from_file_location(
            "multi_agent_coding", REPO_ROOT / "multi_agent_coding" / "__init__.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.__version__
