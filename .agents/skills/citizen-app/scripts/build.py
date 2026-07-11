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
ACCEPTANCE_PATH = Path(".plan/acceptance.json")


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


def load_acceptance_mapping(tests: list[Path], expected_criteria: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(ACCEPTANCE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"error: acceptance mapping is missing or invalid: {exc}") from exc
    criteria = payload.get("criteria") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or payload.get("schema_version") != 1
        or not isinstance(criteria, list)
        or not criteria
    ):
        sys.exit("error: acceptance mapping has an unsupported or empty schema")
    known_files = {path.as_posix() for path in tests}
    mapped_criteria: list[str] = []
    for item in criteria:
        if not isinstance(item, dict) or not isinstance(item.get("criterion"), str):
            sys.exit("error: acceptance mapping contains an invalid criterion")
        mapped_criteria.append(item["criterion"])
        mapped_tests = item.get("tests")
        assertions = item.get("preview_assertions")
        if not isinstance(mapped_tests, list) or not mapped_tests:
            sys.exit("error: every acceptance criterion must name at least one test")
        if not all(
            isinstance(node, str) and node.split("::", 1)[0] in known_files for node in mapped_tests
        ):
            sys.exit("error: acceptance mapping refers to a non-application test")
        if not isinstance(assertions, list) or not all(
            isinstance(value, str) and value.strip() for value in assertions
        ):
            sys.exit("error: preview_assertions must be a list of names")
    if mapped_criteria != expected_criteria:
        sys.exit("error: acceptance mapping must cover every approved criterion in order")
    return payload


def collect_test_names(tests: list[Path]) -> tuple[dict[str, Any], list[str]]:
    check = run_check(
        "collect application tests",
        ["uv", "run", "pytest", "--collect-only", "-q", *[test.as_posix() for test in tests]],
    )
    names = [line.strip() for line in check["stdout"].splitlines() if "::test_" in line]
    if not names:
        check["passed"] = False
    return check, names


def write_evidence(
    path: Path,
    checks: list[dict[str, Any]],
    tests: list[Path],
    collected: list[str],
    acceptance: dict[str, Any],
) -> None:
    state = workflow_state.load()
    payload = {
        "schema_version": 1,
        "run_at": datetime.now(UTC).isoformat(),
        "result": "passed" if all(check["passed"] for check in checks) else "failed",
        "project_fingerprint": workflow_state.project_fingerprint(),
        "plan_fingerprint": state["plan"]["fingerprint"],
        "application_tests": [test.as_posix() for test in tests],
        "collected_application_tests": collected,
        "acceptance_mapping": ACCEPTANCE_PATH.as_posix(),
        "acceptance_mapping_fingerprint": workflow_state.file_fingerprint(ACCEPTANCE_PATH),
        "acceptance_criteria": acceptance["criteria"],
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
    requirements = state.get("requirements")
    expected_criteria = requirements.get("acceptance_criteria", [])
    if not isinstance(expected_criteria, list) or not all(
        isinstance(value, str) for value in expected_criteria
    ):
        sys.exit("error: approved acceptance criteria are missing")
    acceptance = load_acceptance_mapping(tests, expected_criteria)
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
    collection_check, collected = collect_test_names(tests)
    checks = [collection_check, *[run_check(label, command) for label, command in commands]]
    write_evidence(args.evidence, checks, tests, collected, acceptance)

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
