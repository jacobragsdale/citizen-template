#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Run the complete local validation gate and write state-recordable evidence."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

STATE_PATH = Path(".plan/state.json")
DEFAULT_EVIDENCE = Path(".plan/validation/summary.txt")


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    return env


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def print_tail(text: str, lines: int = 15) -> None:
    relevant = [line for line in text.splitlines() if line.strip()]
    if relevant:
        print("--- last dashboard server output:")
        for line in relevant[-lines:]:
            print(f"    {line}")


def run(command: list[str], label: str) -> bool:
    print(f"\n=== {label} ===")
    result = subprocess.run(command, check=False, env=clean_env())
    passed = result.returncode == 0
    print(f"--- {label}: {'PASS' if passed else 'FAIL'}")
    return passed


def resolve_type(explicit: str | None) -> str:
    if explicit:
        return explicit
    if STATE_PATH.is_file():
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        app_type = raw.get("app_type")
        if app_type in {"ui", "job"}:
            return str(app_type)
    sys.exit("error: app type is unknown; pass --type ui|job or record it in state")


def smoke_ui_server() -> bool:
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
    print(f"\n=== dashboard server starts on port {port} ===")
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=clean_env(),
    )
    health = f"http://127.0.0.1:{port}/_stcore/health"
    try:
        for _ in range(30):
            if process.poll() is not None:
                print("--- dashboard server starts: FAIL")
                output, _ = process.communicate()
                print_tail(output)
                return False
            try:
                with urllib.request.urlopen(health, timeout=1) as response:
                    if response.status == 200 and response.read().strip() == b"ok":
                        print("--- dashboard server starts: PASS")
                        return True
            except (OSError, TimeoutError):
                pass
            time.sleep(1)
        print("--- dashboard server starts: FAIL")
        process.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            output, _ = process.communicate(timeout=5)
            print_tail(output)
        return False
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


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
    state_script = Path(__file__).with_name("state.py")
    result = subprocess.run(
        [sys.executable, str(state_script), *args],
        check=False,
        env=clean_env(),
    )
    return result.returncode == 0


def write_evidence(path: Path, results: list[tuple[str, bool]]) -> None:
    failed = [label for label, passed in results if not passed]
    lines = [
        "Citizen app local validation",
        f"Run at: {datetime.now(UTC).isoformat()}",
        "",
        *(f"[{'PASS' if passed else 'FAIL'}] {label}" for label, passed in results),
        "",
        "ALL CHECKS PASSED" if not failed else f"FAILED: {', '.join(failed)}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    dependency_check = (
        (["uv", "lock", "--check"], "dependencies lock is current")
        if os.environ.get("UV_NO_SYNC") == "1"
        else (["uv", "sync", "--quiet"], "dependencies install")
    )
    checks = [
        dependency_check,
        (["uv", "run", "ruff", "check", "."], "lint"),
        (["uv", "run", "ruff", "format", "--check", "."], "format"),
        (["uv", "run", "basedpyright"], "types"),
        (["uv", "run", "pytest", "-q"], "tests"),
    ]
    results = [(label, run(command, label)) for command, label in checks]

    preview_script = Path(__file__).with_name("preview.py")
    render_passed = run(
        [
            "uv",
            "run",
            str(preview_script),
            "--type",
            app_type,
            "--output-dir",
            ".plan/validation/preview",
        ],
        "dashboard renders" if app_type == "ui" else "job dry run",
    )
    results.append(("type-specific execution", render_passed))
    if app_type == "ui":
        results.append(("dashboard server starts", smoke_ui_server()))

    write_evidence(args.evidence, results)
    print("\n" + "=" * 40 + "\nSUMMARY")
    for label, passed in results:
        print(f"[{'PASS' if passed else 'FAIL'}] {label}")

    failures = [label for label, passed in results if not passed]
    if not failures and record_in_state:
        recorded = run_state_command("record-validation", "--evidence", str(args.evidence))
        if not recorded:
            results.append(("state evidence recorded", False))
            write_evidence(args.evidence, results)
            failures.append("state evidence recorded")
    if failures:
        print(f"\n{len(failures)} check(s) failed. Evidence: {args.evidence}")
        return 1
    print(f"\nALL CHECKS PASSED\nEvidence: {args.evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
