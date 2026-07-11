#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run the build-stage quality checks and record fingerprinted evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import state as workflow_state

DEFAULT_EVIDENCE = Path(".plan/build/summary.json")


def application_tests() -> list[Path]:
    return sorted(
        path
        for path in Path("tests").glob("test_*.py")
        if path.name not in workflow_state.TEMPLATE_TEST_FILES
    )


def run_check(label: str, command: list[str]) -> dict[str, Any]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"},
        check=False,
    )
    return {
        "label": label,
        "command": command,
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def write_evidence(path: Path, checks: list[dict[str, Any]], tests: list[Path]) -> None:
    payload = {
        "schema_version": 1,
        "run_at": datetime.now(UTC).isoformat(),
        "result": "passed" if all(check["passed"] for check in checks) else "failed",
        "project_fingerprint": workflow_state.project_fingerprint(),
        "application_tests": [test.as_posix() for test in tests],
        "checks": checks,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument(
        "--no-record",
        action="store_true",
        help="write evidence without invoking state.py record-build",
    )
    args = parser.parse_args()

    tests = application_tests()
    if not tests:
        print("error: no application-specific tests were found", file=sys.stderr)
        return 1

    state = workflow_state.load()
    app_type = state.get("app_type")
    entrypoint = Path("src/app/ui.py" if app_type == "ui" else "src/app/job.py")
    commands = [
        ("lint", ["uv", "run", "ruff", "check", "."]),
        ("format", ["uv", "run", "ruff", "format", "--check", "."]),
        ("types", ["uv", "run", "basedpyright"]),
        (
            "application tests",
            ["uv", "run", "pytest", "-q", *[test.as_posix() for test in tests]],
        ),
        (
            "entry point compiles",
            ["uv", "run", "python", "-m", "py_compile", "src/app/core.py", str(entrypoint)],
        ),
    ]
    checks = [run_check(label, command) for label, command in commands]
    write_evidence(args.evidence, checks, tests)

    for check in checks:
        print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['label']}")
    print(f"Evidence: {args.evidence}")

    if not all(check["passed"] for check in checks):
        return 1
    if args.no_record:
        return 0
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("state.py")),
            "record-build",
            "--evidence",
            str(args.evidence),
        ],
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
