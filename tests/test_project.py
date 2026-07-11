import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PROJECT_SCRIPT = ROOT / ".agents/skills/citizen-app/scripts/project.py"


def run_project(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROJECT_SCRIPT), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_identity_and_starter_helpers_support_utf8_space_path(tmp_path: Path) -> None:
    workspace = tmp_path / "Citizen Apps" / "café demo"
    workspace.mkdir(parents=True)
    (workspace / "pyproject.toml").write_text(
        '[project]\nname = "citizen-app-template"\n', encoding="utf-8"
    )

    identity = run_project(workspace, "set-identity", "--name", "citizen-cafe", "--skip-lock")
    starter = run_project(workspace, "apply-starter", "--type", "job", "--skip-dependencies")
    repeated = run_project(workspace, "apply-starter", "--type", "job", "--skip-dependencies")

    assert identity.returncode == 0, identity.stderr
    assert 'name = "citizen-cafe"' in (workspace / "pyproject.toml").read_text(encoding="utf-8")
    assert starter.returncode == 0, starter.stderr
    assert json.loads(starter.stdout)["result"] == "ready"
    assert json.loads(repeated.stdout)["files"]["src/app/job.py"] == "unchanged"


def test_starter_helper_refuses_to_overwrite_application_work(tmp_path: Path) -> None:
    first = run_project(tmp_path, "apply-starter", "--type", "job", "--skip-dependencies")
    assert first.returncode == 0, first.stderr
    (tmp_path / "src/app/core.py").write_text("custom work\n", encoding="utf-8")

    result = run_project(tmp_path, "apply-starter", "--type", "job", "--skip-dependencies")

    assert result.returncode == 1
    assert "already contains application work" in result.stderr


def test_inspect_reports_application_without_shell_redirection(tmp_path: Path) -> None:
    workspace = tmp_path / "citizen-café"
    (workspace / ".plan").mkdir(parents=True)
    (workspace / ".plan/state.json").write_text("{}\n", encoding="utf-8")

    result = run_project(workspace, "inspect")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["is_application"] is True
    assert payload["remote_url"] is None
