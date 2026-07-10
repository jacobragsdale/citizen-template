import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]
PREVIEW_SCRIPT = ROOT / ".agents/skills/citizen-app/scripts/preview.py"


def load_preview() -> ModuleType:
    spec = importlib.util.spec_from_file_location("citizen_preview", PREVIEW_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_job_preview_executes_dry_run_and_writes_evidence(tmp_path: Path) -> None:
    package = tmp_path / "app"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "job.py").write_text(
        "if __name__ == '__main__':\n"
        "    import sys\n"
        "    assert '--dry-run' in sys.argv\n"
        "    print('DRY RUN — report prepared')\n"
    )
    output_dir = tmp_path / ".plan/preview"

    result = subprocess.run(
        [
            sys.executable,
            str(PREVIEW_SCRIPT),
            "--type",
            "job",
            "--output-dir",
            str(output_dir),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (output_dir / "job-output.txt").read_text() == "DRY RUN — report prepared\n"


def test_ui_preview_executes_page_and_rejects_render_exceptions() -> None:
    preview = load_preview()

    app_test_program = preview.UI_APP_TEST

    assert "AppTest.from_file" in app_test_program
    assert "if app.exception" in app_test_program
    assert "DASHBOARD RENDERED" in app_test_program
