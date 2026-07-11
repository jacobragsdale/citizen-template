#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run the complete local validation gate and write revision-bound evidence."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import state as workflow_state

STATE_PATH = Path(".plan/state.json")
DEFAULT_EVIDENCE = Path(".plan/validation/summary.json")


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    return env


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def diagnostic_path(directory: Path, number: int, label: str) -> Path:
    slug = "-".join(part for part in label.lower().replace("/", " ").split() if part)
    return directory / "diagnostics" / f"{number:02d}-{slug}.log"


def run(command: list[str], label: str, log_path: Path) -> dict[str, Any]:
    started = time.monotonic()
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=clean_env(),
    )
    duration = round(time.monotonic() - started, 3)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        f"$ {' '.join(command)}\n\nSTDOUT\n{result.stdout}\nSTDERR\n{result.stderr}",
        encoding="utf-8",
    )
    passed = result.returncode == 0
    print(f"[{'PASS' if passed else 'FAIL'}] {label}")
    return {
        "label": label,
        "command": command,
        "exit_code": result.returncode,
        "duration_seconds": duration,
        "diagnostic_log": log_path.as_posix(),
    }


def resolve_type(explicit: str | None) -> str:
    if explicit:
        return explicit
    if STATE_PATH.is_file():
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        app_type = raw.get("app_type")
        if app_type in {"ui", "job"}:
            return str(app_type)
    sys.exit("error: app type is unknown; pass --type ui|job or record it in state")


def application_test_files() -> list[Path]:
    return sorted(
        path
        for path in Path("tests").glob("test_*.py")
        if path.name not in workflow_state.TEMPLATE_TEST_FILES
    )


def collected_tests(files: list[Path]) -> list[str]:
    if not files:
        return []
    result = subprocess.run(
        ["uv", "run", "pytest", "--collect-only", "-q", *[path.as_posix() for path in files]],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=clean_env(),
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if "::test_" in line]


def smoke_ui_server(log_path: Path) -> dict[str, Any]:
    port = free_port()
    command = ["uv", "run"]
    if Path(".env").is_file():
        command.extend(("--env-file", ".env"))
    command.extend(
        (
            "streamlit",
            "run",
            "src/app/ui.py",
            "--server.headless=true",
            f"--server.port={port}",
            "--server.address=127.0.0.1",
        )
    )
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=clean_env(),
    )
    exit_code = 1
    output = ""
    try:
        for _ in range(30):
            if process.poll() is not None:
                break
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/_stcore/health", timeout=1
                ) as response:
                    if response.status == 200 and response.read().strip() == b"ok":
                        exit_code = 0
                        break
            except (OSError, TimeoutError):
                pass
            time.sleep(1)
    finally:
        if process.poll() is None:
            process.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            output, _ = process.communicate(timeout=5)
        if process.poll() is None:
            process.kill()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8")
    passed = exit_code == 0
    print(f"[{'PASS' if passed else 'FAIL'}] dashboard server starts")
    return {
        "label": "dashboard server starts",
        "command": command,
        "exit_code": exit_code,
        "duration_seconds": round(time.monotonic() - started, 3),
        "diagnostic_log": log_path.as_posix(),
    }


def current_stage() -> str | None:
    if not STATE_PATH.is_file():
        return None
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    stage = raw.get("stage")
    return str(stage) if isinstance(stage, str) else None


def run_state_command(*args: str) -> bool:
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("state.py")), *args],
        check=False,
        env=clean_env(),
    )
    return result.returncode == 0


def write_evidence(
    path: Path,
    checks: list[dict[str, Any]],
    application_tests: list[str],
    workflow_tests: list[str],
) -> None:
    state = workflow_state.load()
    passed = bool(application_tests) and all(check["exit_code"] == 0 for check in checks)
    payload = {
        "schema_version": 1,
        "run_at": datetime.now(UTC).isoformat(),
        "result": "passed" if passed else "failed",
        "project_fingerprint": workflow_state.project_fingerprint(),
        "plan_fingerprint": state["plan"]["fingerprint"],
        "application_tests": application_tests,
        "workflow_tests": workflow_tests,
        "checks": checks,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = path.with_name("summary.txt")
    failed = [check["label"] for check in checks if check["exit_code"] != 0]
    lines = [
        "Citizen app local validation",
        *(
            f"[{'PASS' if check['exit_code'] == 0 else 'FAIL'}] {check['label']}"
            for check in checks
        ),
        "",
        (
            "ALL CHECKS PASSED"
            if passed
            else f"FAILED: {', '.join(failed) or 'application tests missing'}"
        ),
    ]
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", choices=("ui", "job"), default=None)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    app_type = resolve_type(args.type)
    record_in_state = current_stage() == "validate"
    if record_in_state and not run_state_command("rewind", "validate"):
        print("error: could not clear the previous validation evidence", file=sys.stderr)
        return 1

    evidence_dir = args.evidence.parent
    if (evidence_dir / "diagnostics").exists():
        shutil.rmtree(evidence_dir / "diagnostics")
    for path in evidence_dir.glob("summary.*"):
        path.unlink()
    app_files = application_test_files()
    app_tests = collected_tests(app_files)
    workflow_files = sorted(
        path
        for path in Path("tests").glob("test_*.py")
        if path.name in workflow_state.TEMPLATE_TEST_FILES
    )
    workflow_tests = collected_tests(workflow_files)
    dependency = (
        (["uv", "lock", "--check"], "dependencies lock is current")
        if os.environ.get("UV_NO_SYNC") == "1"
        else (["uv", "sync", "--quiet"], "dependencies install")
    )
    commands = [
        dependency,
        (["uv", "run", "ruff", "check", "."], "lint"),
        (["uv", "run", "ruff", "format", "--check", "."], "format"),
        (["uv", "run", "basedpyright"], "types"),
        (["uv", "run", "pytest", "-q"], "tests"),
    ]
    checks = [
        run(command, label, diagnostic_path(evidence_dir, index, label))
        for index, (command, label) in enumerate(commands, start=1)
    ]
    preview_label = "dashboard renders" if app_type == "ui" else "job dry run"
    checks.append(
        run(
            [
                "uv",
                "run",
                str(Path(__file__).with_name("preview.py")),
                "--type",
                app_type,
                "--output-dir",
                ".plan/validation/preview",
            ],
            preview_label,
            diagnostic_path(evidence_dir, len(checks) + 1, preview_label),
        )
    )
    if app_type == "ui":
        checks.append(
            smoke_ui_server(
                diagnostic_path(evidence_dir, len(checks) + 1, "dashboard server starts")
            )
        )

    write_evidence(args.evidence, checks, app_tests, workflow_tests)
    failed = [check["label"] for check in checks if check["exit_code"] != 0]
    if not app_tests:
        failed.append("application tests missing")
    if (
        not failed
        and record_in_state
        and not run_state_command("record-validation", "--evidence", str(args.evidence))
    ):
        failed.append("state evidence recorded")
    if failed:
        summary = args.evidence.with_name("summary.txt")
        print(f"Validation failed: {', '.join(failed)}. See {summary}.")
        return 1
    print(f"ALL CHECKS PASSED\nEvidence: {args.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
