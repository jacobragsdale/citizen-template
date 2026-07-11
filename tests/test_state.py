import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
STATE_SCRIPT = ROOT / ".agents/skills/citizen-app/scripts/state.py"


def run_state(workspace: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(STATE_SCRIPT), *args],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def require_success(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def begin_workflow(workspace: Path) -> None:
    require_success(run_state(workspace, "init", "--name", "citizen-example"))
    require_success(run_state(workspace, "set", "repo_provider", "github"))
    require_success(run_state(workspace, "set", "repo_visibility", "private"))
    require_success(
        run_state(workspace, "set", "repo_url", "https://github.com/example/citizen-example")
    )
    require_success(run_state(workspace, "set", "workspace_ready", "true"))
    require_success(run_state(workspace, "advance"))
    require_success(run_state(workspace, "set", "app_type", "ui"))
    require_success(run_state(workspace, "advance"))


def approve_plan(workspace: Path) -> None:
    plan_dir = workspace / ".plan"
    plan_dir.mkdir(exist_ok=True)
    (plan_dir / "PLAN.md").write_text(
        "# Plan — café report\n\nBuild a useful dashboard.\n", encoding="utf-8"
    )
    requirements = {
        "goal": "Show the weekly result",
        "acceptance_criteria": ["The weekly result is visible"],
        "env": [],
    }
    require_success(run_state(workspace, "set", "requirements", json.dumps(requirements)))
    require_success(run_state(workspace, "advance"))
    require_success(run_state(workspace, "approve-plan"))
    require_success(run_state(workspace, "advance"))


def write_application(workspace: Path) -> None:
    (workspace / "src/app").mkdir(parents=True)
    (workspace / "tests").mkdir()
    (workspace / "README.md").write_text("# Example\n", encoding="utf-8")
    (workspace / "pyproject.toml").write_text(
        "[project]\nname='citizen-example'\n", encoding="utf-8"
    )
    (workspace / "uv.lock").write_text("", encoding="utf-8")
    (workspace / ".env.example").write_text("# Configuration names only.\n", encoding="utf-8")
    (workspace / "src/app/core.py").write_text(
        "def total() -> int:\n    return 7\n", encoding="utf-8"
    )
    (workspace / "src/app/ui.py").write_text(
        "from app.core import total\n\nprint(total())\n", encoding="utf-8"
    )
    (workspace / "tests/test_total.py").write_text(
        "from app.core import total\n\n\ndef test_weekly_total_is_visible() -> None:\n"
        "    result = total()\n\n    assert result == 7\n",
        encoding="utf-8",
    )


def record_build(workspace: Path) -> None:
    fingerprint = run_state(workspace, "fingerprint", "project").stdout.strip()
    evidence = workspace / ".plan/build/summary.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "result": "passed",
                "project_fingerprint": fingerprint,
                "application_tests": ["tests/test_total.py"],
                "checks": [{"label": "application tests", "passed": True}],
            }
        ),
        encoding="utf-8",
    )
    require_success(run_state(workspace, "record-build", "--evidence", str(evidence)))


def record_through_ship(workspace: Path) -> None:
    write_application(workspace)
    record_build(workspace)
    require_success(run_state(workspace, "advance"))

    evidence = workspace / ".plan/preview/ui-summary.txt"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("DASHBOARD RENDERED\n", encoding="utf-8")
    require_success(run_state(workspace, "record-preview", "--evidence", str(evidence)))
    require_success(run_state(workspace, "advance"))
    require_success(run_state(workspace, "approve-preview"))
    require_success(run_state(workspace, "advance"))

    validation = workspace / ".plan/validation/summary.txt"
    validation.parent.mkdir(parents=True)
    validation.write_text("[PASS] checks\n\nALL CHECKS PASSED\n", encoding="utf-8")
    require_success(run_state(workspace, "record-validation", "--evidence", str(validation)))
    require_success(run_state(workspace, "advance"))

    (workspace / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
    require_success(
        run_state(
            workspace,
            "record-image",
            "--tag",
            "citizen-example:local",
            "--image-id",
            "sha256:abc123",
        )
    )
    require_success(run_state(workspace, "advance"))


def test_stage_cannot_be_changed_through_generic_set(tmp_path: Path) -> None:
    require_success(run_state(tmp_path, "init", "--name", "citizen-example"))

    result = run_state(tmp_path, "set", "stage", "done")

    assert result.returncode == 1
    assert "cannot be set directly" in result.stderr


def test_show_treats_a_brand_new_workspace_as_a_normal_start(tmp_path: Path) -> None:
    result = run_state(tmp_path, "show")

    assert result.returncode == 0
    assert "start with the scaffold stage" in result.stdout


def test_missing_scaffold_and_type_inputs_block_advancement(tmp_path: Path) -> None:
    require_success(run_state(tmp_path, "init", "--name", "citizen-example"))

    scaffold_result = run_state(tmp_path, "advance")
    require_success(run_state(tmp_path, "set", "repo_provider", "local"))
    require_success(run_state(tmp_path, "set", "repo_visibility", "local"))
    require_success(run_state(tmp_path, "set", "workspace_ready", "true"))
    require_success(run_state(tmp_path, "advance"))
    type_result = run_state(tmp_path, "advance")

    assert scaffold_result.returncode == 2
    assert "working repository" in scaffold_result.stderr
    assert type_result.returncode == 2
    assert "dashboard versus automated-job" in type_result.stderr


def test_complete_current_evidence_chain_reaches_done(tmp_path: Path) -> None:
    begin_workflow(tmp_path)
    approve_plan(tmp_path)
    record_through_ship(tmp_path)
    require_success(
        run_state(
            tmp_path,
            "record-pr",
            "--url",
            "https://github.com/example/citizen-example/pull/1",
        )
    )

    require_success(run_state(tmp_path, "advance"))

    assert run_state(tmp_path, "stage").stdout.strip() == "done"


def test_code_change_rejects_old_preview_approval(tmp_path: Path) -> None:
    begin_workflow(tmp_path)
    approve_plan(tmp_path)
    write_application(tmp_path)
    record_build(tmp_path)
    require_success(run_state(tmp_path, "advance"))
    evidence = tmp_path / ".plan/preview/ui-summary.txt"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("DASHBOARD RENDERED\n", encoding="utf-8")
    require_success(run_state(tmp_path, "record-preview", "--evidence", str(evidence)))
    require_success(run_state(tmp_path, "advance"))
    (tmp_path / "src/app/core.py").write_text(
        "def total() -> int:\n    return 8\n", encoding="utf-8"
    )

    result = run_state(tmp_path, "approve-preview")

    assert result.returncode == 1
    assert "stale" in result.stderr


def test_requirements_change_rewinds_and_clears_plan_approval(tmp_path: Path) -> None:
    begin_workflow(tmp_path)
    approve_plan(tmp_path)
    changed = {
        "goal": "Show a revised result",
        "acceptance_criteria": ["The revised result is visible"],
    }

    require_success(run_state(tmp_path, "set", "requirements", json.dumps(changed)))
    state = json.loads(run_state(tmp_path, "show", "--json").stdout)

    assert state["stage"] == "interview"
    assert state["plan"]["approved"] is False
    assert state["build"]["recorded"] is False


def test_non_https_pull_request_url_is_rejected(tmp_path: Path) -> None:
    begin_workflow(tmp_path)
    approve_plan(tmp_path)
    record_through_ship(tmp_path)

    result = run_state(tmp_path, "record-pr", "--url", "not-a-pull-request")

    assert result.returncode == 1
    assert "HTTPS" in result.stderr


def test_old_completed_workflow_rewinds_instead_of_reusing_unverifiable_evidence(
    tmp_path: Path,
) -> None:
    plan_dir = tmp_path / ".plan"
    plan_dir.mkdir()
    (plan_dir / "state.json").write_text(
        json.dumps(
            {
                "stage": "done",
                "app_name": "citizen-old",
                "app_type": "ui",
                "repo_url": "https://github.com/example/citizen-old",
                "requirements": {
                    "goal": "Show the old result",
                    "acceptance_criteria": ["The result is visible"],
                },
                "plan_approved": True,
                "validation": {"passed": True},
                "image_built": True,
                "pr_url": "https://github.com/example/citizen-old/pull/1",
            }
        ),
        encoding="utf-8",
    )

    state = json.loads(run_state(tmp_path, "show", "--json").stdout)

    assert state["version"] == 3
    assert state["stage"] == "plan-review"
    assert state["plan"]["fingerprint"] is None
    assert state["preview"]["approved"] is False


def test_requirements_can_be_read_from_a_utf8_file(tmp_path: Path) -> None:
    require_success(run_state(tmp_path, "init", "--name", "citizen-example"))
    requirements = tmp_path / "requirements.json"
    requirements.write_text(
        json.dumps(
            {
                "goal": "Show café totals — clearly",
                "acceptance_criteria": ["The café total is visible"],
            }
        ),
        encoding="utf-8",
    )

    require_success(
        run_state(
            tmp_path,
            "set",
            "requirements",
            "--value-file",
            str(requirements),
        )
    )

    state = json.loads(run_state(tmp_path, "show", "--json").stdout)
    assert state["requirements"]["goal"] == "Show café totals — clearly"


def test_external_container_evidence_must_match_current_fingerprints(tmp_path: Path) -> None:
    begin_workflow(tmp_path)
    approve_plan(tmp_path)
    record_through_ship(tmp_path)
    require_success(run_state(tmp_path, "rewind", "containerize"))
    evidence = tmp_path / ".plan/container/external.json"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "result": "passed",
                "runtime_passed": True,
                "project_fingerprint": run_state(tmp_path, "fingerprint", "project").stdout.strip(),
                "dockerfile_fingerprint": run_state(
                    tmp_path, "fingerprint", "dockerfile"
                ).stdout.strip(),
                "tag": "citizen-example:external",
                "image_id": "sha256:external123",
            }
        ),
        encoding="utf-8",
    )

    require_success(
        run_state(
            tmp_path,
            "record-container-verification",
            "--evidence",
            str(evidence),
        )
    )

    state = json.loads(run_state(tmp_path, "show", "--json").stdout)
    assert state["container"]["method"] == "external"
    assert state["container"]["image_id"] == "sha256:external123"


def test_generated_python_bytecode_does_not_change_project_fingerprint(tmp_path: Path) -> None:
    begin_workflow(tmp_path)
    before = run_state(tmp_path, "fingerprint", "project").stdout.strip()
    cache = tmp_path / "src/app/__pycache__"
    cache.mkdir(parents=True)
    (cache / "core.cpython-311.pyc").write_bytes(b"generated bytecode")

    after = run_state(tmp_path, "fingerprint", "project").stdout.strip()

    assert after == before
