"""Execute deterministic citizen-app scenarios inside the no-admin Windows guest."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATE_SCRIPT = Path(".agents/skills/citizen-app/scripts/state.py")
BUILD_SCRIPT = Path(".agents/skills/citizen-app/scripts/build.py")
PREVIEW_SCRIPT = Path(".agents/skills/citizen-app/scripts/preview.py")
VALIDATE_SCRIPT = Path(".agents/skills/citizen-app/scripts/validate.py")


@dataclass
class HarnessRun:
    scenario: str
    evidence_dir: Path
    commands: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        (self.evidence_dir / "stdout").mkdir(exist_ok=True)
        (self.evidence_dir / "stderr").mkdir(exist_ok=True)

    def run(
        self,
        label: str,
        command: list[str],
        *,
        expected: tuple[int, ...] = (0,),
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        started = time.monotonic()
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
        index = len(self.commands) + 1
        stdout_path = self.evidence_dir / "stdout" / f"{index:03d}-{slug(label)}.txt"
        stderr_path = self.evidence_dir / "stderr" / f"{index:03d}-{slug(label)}.txt"
        stdout_path.write_text(result.stdout, encoding="utf-8")
        stderr_path.write_text(result.stderr, encoding="utf-8")
        record = {
            "label": label,
            "command": command,
            "exit_code": result.returncode,
            "expected_exit_codes": list(expected),
            "passed": result.returncode in expected,
            "duration_seconds": round(time.monotonic() - started, 3),
            "stdout": stdout_path.relative_to(self.evidence_dir).as_posix(),
            "stderr": stderr_path.relative_to(self.evidence_dir).as_posix(),
        }
        self.commands.append(record)
        self.write_commands()
        if result.returncode not in expected:
            raise RuntimeError(
                f"{label} returned {result.returncode}, expected {expected}:\n"
                f"{result.stdout}{result.stderr}"
            )
        return result

    def state(self, label: str, *arguments: str, expected: tuple[int, ...] = (0,)) -> str:
        result = self.run(
            label,
            [sys.executable, str(STATE_SCRIPT), *arguments],
            expected=expected,
        )
        return result.stdout + result.stderr

    def write_commands(self) -> None:
        path = self.evidence_dir / "commands.jsonl"
        text = "".join(json.dumps(command) + "\n" for command in self.commands)
        path.write_text(text, encoding="utf-8")


def slug(value: str) -> str:
    return "-".join(part for part in value.lower().replace("_", " ").split() if part)


def write(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def requirements_payload(app_type: str, *, revised: bool = False) -> dict[str, Any]:
    if app_type == "ui":
        criteria = [
            "The page clearly labels the stock rows as sample data",
            "Average price and volume are visible",
            "A user can compare one or more symbols",
        ]
        if revised:
            criteria.append("An empty symbol selection shows friendly guidance")
        return {
            "goal": "Compare sample stock prices and volume — without a spreadsheet",
            "acceptance_criteria": criteria,
            "data_sources": ["stocks"],
            "env": [],
        }
    return {
        "goal": "Prepare a plain-text bond summary — safely and repeatably",
        "acceptance_criteria": [
            "The output includes the bond record count",
            "Numeric fields include minimum, maximum, and average values",
            "A successful run exits with code zero",
        ],
        "data_sources": ["bonds"],
        "env": [],
    }


def scaffold(run: HarnessRun, app_type: str, *, revised: bool = False) -> None:
    run.run(
        "run external-container preflight",
        [
            "uv",
            "run",
            ".agents/skills/citizen-app/scripts/preflight.py",
            "--provider",
            "local",
            "--container-mode",
            "external",
        ],
    )
    app_name = "citizen-harness-dashboard" if app_type == "ui" else "citizen-harness-job"
    run.state("initialize workflow", "init", "--name", app_name)
    run.state("record local provider", "set", "repo_provider", "local")
    run.state("record local visibility", "set", "repo_visibility", "local")
    run.state("record workspace readiness", "set", "workspace_ready", "true")
    run.state("advance scaffold", "advance")
    run.state("record application type", "set", "app_type", app_type)
    run.state("advance type choice", "advance")
    plan = (
        "# Harness plan — café-safe Windows evidence\n\n"
        f"Build a {'stock comparison dashboard' if app_type == 'ui' else 'bond summary job'}.\n"
    )
    if revised:
        plan += "\nThe revised result includes a friendly empty-selection state.\n"
    write(".plan/PLAN.md", plan)
    requirements_path = Path(".plan/requirements.json")
    write(requirements_path, json.dumps(requirements_payload(app_type, revised=revised), indent=2))
    run.state(
        "record structured requirements",
        "set",
        "requirements",
        "--value-file",
        str(requirements_path),
    )
    run.state("advance interview", "advance")
    run.state("approve plan", "approve-plan")
    run.state("advance plan review", "advance")


DASHBOARD_CORE = """from __future__ import annotations

from app.data import Row, as_float


def selected_rows(rows: list[Row], symbols: list[str]) -> list[Row]:
    wanted = set(symbols)
    return [row for row in rows if str(row["symbol"]) in wanted]


def averages(rows: list[Row]) -> tuple[float, float]:
    if not rows:
        return 0.0, 0.0
    price = sum(as_float(row, "price") for row in rows) / len(rows)
    volume = sum(as_float(row, "volume") for row in rows) / len(rows)
    return price, volume
"""

DASHBOARD_UI = """from __future__ import annotations

import pandas as pd
import streamlit as st

from app.core import averages, selected_rows
from app.data import get_source

st.set_page_config(page_title="Stock comparison", layout="wide")
st.title("Stock comparison")
st.caption("Representative sample data — not live market data")

try:
    rows = get_source("stocks").fetch()
except Exception:
    st.error("The sample stock data could not be read. Try again later.")
    st.stop()

symbols = [str(row["symbol"]) for row in rows]
chosen = st.multiselect("Symbols to compare", symbols, default=symbols)
visible = selected_rows(rows, chosen)
if not visible:
    st.warning("Choose at least one symbol to see the comparison.")
    st.stop()

average_price, average_volume = averages(visible)
left, right = st.columns(2)
left.metric("Average price", f"${average_price:,.2f}")
right.metric("Average volume", f"{average_volume:,.0f}")
frame = pd.DataFrame(visible)
st.dataframe(frame, width="stretch")
st.bar_chart(frame.set_index("symbol")[["price", "volume"]])
"""

DASHBOARD_TEST = """from app.core import averages, selected_rows

ROWS = [
    {"symbol": "AAA", "price": 10.0, "volume": 100},
    {"symbol": "BBB", "price": 20.0, "volume": 300},
]


def test_selected_symbols_are_compared() -> None:
    result = selected_rows(ROWS, ["BBB"])

    assert result == [ROWS[1]]


def test_average_price_and_volume_are_calculated() -> None:
    result = averages(ROWS)

    assert result == (15.0, 200.0)


def test_empty_selection_has_zero_averages() -> None:
    result = averages([])

    assert result == (0.0, 0.0)
"""

JOB_CORE = """from app.data import DataSource
from app.data.summary import summarize


def prepare_summary(source: DataSource) -> str:
    return summarize(source)
"""

JOB_ENTRYPOINT = """from __future__ import annotations

import argparse

from app.core import prepare_summary
from app.data import get_source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.parse_args()
    try:
        print(prepare_summary(get_source("bonds")))
    except Exception as exc:
        print(f"Bond summary failed: {type(exc).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""

JOB_TEST = """from app.core import prepare_summary
from app.data import get_source


def test_bond_summary_includes_count_and_numeric_statistics() -> None:
    result = prepare_summary(get_source("bonds"))

    assert "Bonds: 8 records" in result
    assert "coupon_pct: min=" in result
    assert "yield_pct: min=" in result
    assert "price: min=" in result
"""


def add_dependencies(run: HarnessRun, packages: list[str]) -> None:
    wheelhouse = os.environ.get("UV_FIND_LINKS")
    if os.environ.get("UV_OFFLINE") == "1" and wheelhouse:
        ui_lock = os.environ.get("CITIZEN_HARNESS_UI_LOCK")
        ui_project = os.environ.get("CITIZEN_HARNESS_UI_PROJECT")
        if (
            not ui_lock
            or not Path(ui_lock).is_file()
            or not ui_project
            or not Path(ui_project).is_file()
        ):
            raise RuntimeError("the staged cross-platform UI resolution is missing")
        shutil.copy2(ui_project, "pyproject.toml")
        shutil.copy2(ui_lock, "uv.lock")
        run.run("verify staged dashboard resolution", ["uv", "lock", "--check"])
        run.run(
            "install dashboard dependencies offline",
            [
                "uv",
                "pip",
                "install",
                "--python",
                sys.executable,
                "--offline",
                "--find-links",
                wheelhouse,
                *packages,
            ],
        )
    else:
        run.run("add dashboard dependencies", ["uv", "add", *packages])


def write_application(run: HarnessRun, app_type: str) -> None:
    if app_type == "ui":
        add_dependencies(run, ["streamlit", "pandas"])
        write("src/app/core.py", DASHBOARD_CORE)
        write("src/app/ui.py", DASHBOARD_UI)
        write("tests/test_harness_dashboard.py", DASHBOARD_TEST)
    else:
        write("src/app/core.py", JOB_CORE)
        write("src/app/job.py", JOB_ENTRYPOINT)
        write("tests/test_harness_job.py", JOB_TEST)
    write(
        "README.md",
        "# Citizen harness application\n\n"
        "Representative sample data is used for this Windows rehearsal.\n\n"
        "Delivery status: ready for internal pipeline after PR approval.\n",
    )
    if app_type == "ui":
        criteria = [
            {
                "criterion": "The page clearly labels the stock rows as sample data",
                "tests": ["tests/test_harness_dashboard.py::test_selected_symbols_are_compared"],
                "preview_assertions": ["sample_data_label"],
            },
            {
                "criterion": "Average price and volume are visible",
                "tests": [
                    "tests/test_harness_dashboard.py::test_average_price_and_volume_are_calculated",
                ],
                "preview_assertions": ["average_metrics"],
            },
            {
                "criterion": "A user can compare one or more symbols",
                "tests": ["tests/test_harness_dashboard.py::test_selected_symbols_are_compared"],
                "preview_assertions": ["comparison_symbol_count"],
            },
        ]
    else:
        criteria = [
            {
                "criterion": "The output includes the bond record count",
                "tests": [
                    "tests/test_harness_job.py::test_bond_summary_includes_count_and_numeric_statistics"
                ],
                "preview_assertions": ["record_count"],
            },
            {
                "criterion": "Numeric fields include minimum, maximum, and average values",
                "tests": [
                    "tests/test_harness_job.py::test_bond_summary_includes_count_and_numeric_statistics"
                ],
                "preview_assertions": ["numeric_statistics"],
            },
            {
                "criterion": "A successful run exits with code zero",
                "tests": [
                    "tests/test_harness_job.py::test_bond_summary_includes_count_and_numeric_statistics"
                ],
                "preview_assertions": ["dry_run_exit_code"],
            },
        ]
    write(
        ".plan/acceptance.json",
        json.dumps({"schema_version": 1, "criteria": criteria}, indent=2),
    )


def record_build(run: HarnessRun) -> None:
    run.run("run build checks", ["uv", "run", str(BUILD_SCRIPT)])
    run.state("advance build", "advance")


def record_preview_and_approval(run: HarnessRun, app_type: str) -> None:
    run.run("execute preview", ["uv", "run", str(PREVIEW_SCRIPT)])
    run.state("record preview", "record-preview", "--evidence", ".plan/preview/summary.json")
    run.state("advance preview", "advance")
    if app_type == "ui":
        run.state("record controller browser review", "record-browser-review")
    run.state("approve preview", "approve-preview")
    run.state("advance user review", "advance")


def validate_and_package(run: HarnessRun, app_type: str) -> None:
    run.run("validate application", ["uv", "run", str(VALIDATE_SCRIPT)])
    run.state("advance validation", "advance")
    dockerfile = Path(
        ".agents/skills/citizen-app/assets/dockerfiles/"
        + ("Dockerfile.ui" if app_type == "ui" else "Dockerfile.job")
    )
    shutil.copy2(dockerfile, "Dockerfile")
    shutil.copy2(".agents/skills/citizen-app/assets/dockerfiles/dockerignore", ".dockerignore")


def happy_path(run: HarnessRun, app_type: str) -> None:
    scaffold(run, app_type)
    write_application(run, app_type)
    record_build(run)
    record_preview_and_approval(run, app_type)
    validate_and_package(run, app_type)


def revision_stress(run: HarnessRun) -> None:
    scaffold(run, "ui")
    write_application(run, "ui")
    record_build(run)
    run.run("execute first preview", ["uv", "run", str(PREVIEW_SCRIPT)])
    write("src/app/core.py", DASHBOARD_CORE + "\nREVISION_MARKER = 1\n")
    rejected = run.state(
        "reject stale build before preview",
        "record-preview",
        "--evidence",
        ".plan/preview/summary.json",
        expected=(1,),
    )
    if "stale" not in rejected:
        raise RuntimeError("stale build rejection did not explain the fingerprint failure")
    run.state("rewind changed build", "rewind", "build")
    record_build(run)
    record_preview_and_approval(run, "ui")
    write("src/app/ui.py", DASHBOARD_UI + "\n# visible revision\n")
    fake = Path(".plan/validation/stale.txt")
    write(fake, "ALL CHECKS PASSED\n")
    rejected = run.state(
        "reject stale preview before validation",
        "record-validation",
        "--evidence",
        str(fake),
        expected=(1,),
    )
    if "stale" not in rejected:
        raise RuntimeError("stale preview rejection did not explain the fingerprint failure")
    run.state("rewind changed preview", "rewind", "build")
    record_build(run)
    record_preview_and_approval(run, "ui")
    validate_and_package(run, "ui")


def collect_source(evidence_dir: Path) -> None:
    archive = evidence_dir / "source.zip"
    ignored = {".git", ".venv", ".pytest_cache", ".ruff_cache", "__pycache__"}
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(Path.cwd().rglob("*")):
            if not path.is_file() or any(part in ignored for part in path.parts):
                continue
            if path.is_relative_to(evidence_dir):
                continue
            output.write(path, path.relative_to(Path.cwd()).as_posix())


def write_summary(run: HarnessRun, result: str) -> None:
    stage = (
        run.state("read final workflow stage", "stage").strip()
        if Path(".plan/state.json").is_file()
        else None
    )
    summary = {
        "schema_version": 1,
        "scenario": run.scenario,
        "result": result,
        "run_at": datetime.now(UTC).isoformat(),
        "stage": stage,
        "commands": len(run.commands),
    }
    (run.evidence_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    run = HarnessRun(args.scenario, args.evidence_dir.resolve())

    if args.scenario == "bootstrap-smoke":
        environment = json.loads(
            (run.evidence_dir / "environment.json").read_text(encoding="utf-8")
        )
        if environment.get("elevated") is not False:
            raise RuntimeError("bootstrap evidence does not prove a standard-user token")
        run.run("verify uv", ["uv", "--version"])
        run.run("verify git", ["git", "--version"])
        run.run("verify python", [sys.executable, "--version"])
        run.run(
            "verify external-container preflight",
            [
                "uv",
                "run",
                ".agents/skills/citizen-app/scripts/preflight.py",
                "--provider",
                "local",
                "--container-mode",
                "external",
            ],
        )
    elif args.scenario in {"dashboard-happy", "encoding-paths"}:
        happy_path(run, "ui")
    elif args.scenario == "missing-browser":
        scaffold(run, "ui")
        write_application(run, "ui")
        record_build(run)
        run.run("execute preview", ["uv", "run", str(PREVIEW_SCRIPT)])
        run.state("record preview", "record-preview", "--evidence", ".plan/preview/summary.json")
        run.state("advance preview", "advance")
        rejected = run.state("reject approval without browser", "approve-preview", expected=(1,))
        if "browser" not in rejected.lower():
            raise RuntimeError("missing-browser rejection was not actionable")
        write(run.evidence_dir / "preview/browser.json", '{"available": false}\n')
    elif args.scenario in {"job-happy", "resume"}:
        happy_path(run, "job")
        if args.scenario == "resume":
            run.state("resume in a fresh process", "show", "--json")
    elif args.scenario == "revision-stress":
        revision_stress(run)
    elif args.scenario == "network-denied":
        command = ["uv", "add", "--offline", "citizen-harness-package-that-does-not-exist"]
        result = run.run("reject unavailable offline dependency", command, expected=(1, 2))
        if "not found" not in (result.stdout + result.stderr).lower():
            raise RuntimeError("offline dependency failure was not actionable")
    else:
        raise ValueError(f"unknown scenario: {args.scenario}")

    if Path("Dockerfile").is_file():
        collect_source(run.evidence_dir)
    write_summary(run, "passed")
    print(run.evidence_dir / "summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
