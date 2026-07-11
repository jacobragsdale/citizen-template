import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).parents[1]
HARNESS_DIR = ROOT / "tools/windows-harness"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_tool_manifest_pins_checksum_verified_user_portable_tools() -> None:
    prepare = load_module("windows_prepare", HARNESS_DIR / "prepare.py")

    manifest = prepare.load_tool_manifest()

    tools = {entry["name"]: entry for entry in manifest["tools"]}
    assert set(tools) == {"uv", "git", "python"}
    assert all(len(entry["sha256"]) == 64 for entry in tools.values())
    assert tools["git"]["filename"].endswith(".zip")
    assert tools["python"]["filename"].endswith(".tar.gz")


def test_source_archive_includes_uncommitted_harness_files_but_not_local_caches(
    tmp_path: Path,
) -> None:
    prepare = load_module("windows_prepare_archive", HARNESS_DIR / "prepare.py")

    archive = prepare.write_source_archive(tmp_path)

    with zipfile.ZipFile(archive) as source:
        names = set(source.namelist())
    assert "tools/windows-harness/bootstrap.ps1" in names
    assert "WINDOWS_TEST_HARNESS_PLAN.md" in names
    assert not any(name.startswith(".venv/") for name in names)
    assert not any(name.startswith(".test-runs/") for name in names)


def test_collector_rejects_elevated_run_evidence(tmp_path: Path) -> None:
    collector = load_module("windows_collect_elevated", HARNESS_DIR / "collect.py")
    (tmp_path / "environment.json").write_text(
        json.dumps({"run_id": "elevated", "elevated": True}), encoding="utf-8"
    )
    (tmp_path / "summary.json").write_text(
        json.dumps({"scenario": "bootstrap-smoke", "result": "passed"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="standard-user"):
        collector.collect(tmp_path)


def test_collector_binds_passing_result_to_returned_source_archive(tmp_path: Path) -> None:
    collector = load_module("windows_collect_passed", HARNESS_DIR / "collect.py")
    (tmp_path / "environment.json").write_text(
        json.dumps(
            {
                "run_id": "job-01",
                "elevated": False,
                "windows_build": "26100",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "summary.json").write_text(
        json.dumps(
            {
                "scenario": "job-happy",
                "result": "passed",
                "stage": "containerize",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "source.zip").write_bytes(b"source archive")

    result = collector.collect(tmp_path)

    assert result["standard_user"] is True
    assert result["stage"] == "containerize"
    assert len(result["source_sha256"]) == 64


def test_bootstrap_refuses_admin_and_uses_only_current_user_storage() -> None:
    bootstrap = (HARNESS_DIR / "bootstrap.ps1").read_text(encoding="utf-8")

    assert "current token is elevated" in bootstrap
    assert "$env:LOCALAPPDATA" in bootstrap
    assert "UV_PYTHON_DOWNLOADS" in bootstrap
    assert "ComputerInfo" in bootstrap
    assert "[char]0x00e9" in bootstrap
    assert "Get-CimInstance" not in bootstrap
    assert "UTF8Encoding($true)" in bootstrap
    assert "offline project install failed" in bootstrap
    assert "UV_NO_SYNC" in bootstrap
    assert "PYTHONPATH" in bootstrap
    assert "CITIZEN_HARNESS_UI_LOCK" in bootstrap
    assert "SetEnvironmentVariable" not in bootstrap
    assert "winget" not in bootstrap.lower()
    assert "winget install" not in bootstrap.lower()
    assert "docker desktop" not in bootstrap.lower()


def test_scenarios_cover_every_planned_fresh_windows_behavior() -> None:
    runner = (HARNESS_DIR / "run-scenario.ps1").read_text(encoding="utf-8")

    for scenario in (
        "bootstrap-smoke",
        "dashboard-happy",
        "job-happy",
        "revision-stress",
        "encoding-paths",
        "resume",
        "network-denied",
        "missing-browser",
    ):
        assert scenario in runner


def test_controller_can_leave_a_dashboard_running_for_browser_review() -> None:
    controller = (HARNESS_DIR / "harness.py").read_text(encoding="utf-8")

    assert "--keep-running" in controller
    assert "/_stcore/health" in controller
    assert "controller-health.json" in controller
    assert "final-state.json" in controller
    assert "container-verification.json" in controller
    assert "Set-ExecutionPolicy -Scope Process Bypass" in controller


def test_offline_dashboard_uses_a_controller_resolved_cross_platform_lock() -> None:
    prepare = (HARNESS_DIR / "prepare.py").read_text(encoding="utf-8")
    scenario = (HARNESS_DIR / "scenario.py").read_text(encoding="utf-8")

    assert "prepare_ui_resolution" in prepare
    assert '"ui-pyproject.toml"' in prepare
    assert '"ui-uv.lock"' in prepare
    assert 'shutil.copy2(ui_project, "pyproject.toml")' in scenario
    assert 'shutil.copy2(ui_lock, "uv.lock")' in scenario
