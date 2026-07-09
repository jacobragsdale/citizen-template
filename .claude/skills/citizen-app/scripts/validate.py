#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fail-hard validation gate for a citizen app.

Runs the same checks for every app, plus a type-specific smoke run that proves
the app actually boots. Any failure => nonzero exit and a plain report of what
broke. The build stage loops back here until this exits 0.

On completion this also records the result into .plan/state.json
(`validation.passed` + `validation.last_run`), so the validate gate is DERIVED
from a real run rather than hand-attested. App type is read from that state file
unless --type is given.

  uv run .claude/skills/citizen-app/scripts/validate.py
  uv run .claude/skills/citizen-app/scripts/validate.py --type ui
"""

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


def clean_env() -> dict[str, str]:
    """Environment for uv subcalls with VIRTUAL_ENV dropped.

    A stale VIRTUAL_ENV (e.g. an outer activated venv) makes every `uv run`
    print a "VIRTUAL_ENV does not match the project environment" warning. uv
    still uses the project's .venv; the warning is just noise the citizen
    should never see.
    """
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    return env


def free_port() -> int:
    """An OS-assigned free TCP port, so parallel runs never collide."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def print_tail(text: str, n: int = 15) -> None:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if lines:
        print("--- last server output:")
        for ln in lines[-n:]:
            print(f"    {ln}")


def run(cmd: list[str], label: str) -> bool:
    print(f"\n=== {label}: {' '.join(cmd)} ===")
    result = subprocess.run(cmd, env=clean_env())
    ok = result.returncode == 0
    print(f"--- {label}: {'PASS' if ok else 'FAIL'}")
    return ok


def smoke_job() -> bool:
    return run(["uv", "run", "python", "-m", "app.job", "--dry-run"], "smoke (job dry-run)")


def smoke_ui() -> bool:
    port = free_port()
    print(f"\n=== smoke (streamlit boots): starting headless server on :{port} ===")
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "streamlit",
            "run",
            "src/app/ui.py",
            "--server.headless=true",
            f"--server.port={port}",
            "--server.address=127.0.0.1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=clean_env(),
    )
    health = f"http://127.0.0.1:{port}/_stcore/health"
    try:
        for _ in range(30):  # ~30s: cold uv-run + streamlit startup
            if proc.poll() is not None:
                print("--- smoke (ui): FAIL — server exited during startup")
                print_tail(proc.stdout.read() if proc.stdout else "")
                return False
            try:
                with urllib.request.urlopen(health, timeout=1) as resp:
                    if resp.status == 200 and resp.read().strip() == b"ok":
                        print("--- smoke (ui): PASS — server reported healthy")
                        return True
            except Exception:
                pass
            time.sleep(1)
        print("--- smoke (ui): FAIL — server did not become healthy in 30s")
        proc.terminate()
        with contextlib.suppress(Exception):
            print_tail(proc.stdout.read() if proc.stdout else "")
        return False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def resolve_type(explicit: str | None) -> str:
    if explicit:
        return explicit
    if STATE_PATH.exists():
        t = json.loads(STATE_PATH.read_text()).get("app_type")
        if t in ("ui", "job"):
            return t
    sys.exit("error: app_type unknown — pass --type ui|job or set it in state")


def record(passed: bool) -> None:
    """Write the validate result into state so the gate is derived, not attested."""
    if not STATE_PATH.exists():
        return
    try:
        state = json.loads(STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return
    validation = state.get("validation")
    if not isinstance(validation, dict):
        validation = {}
    validation["passed"] = passed
    validation["last_run"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["validation"] = validation
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--type", choices=["ui", "job"], default=None)
    args = parser.parse_args()
    app_type = resolve_type(args.type)

    checks = [
        (["uv", "sync", "--quiet"], "install deps (uv sync)"),
        (["uv", "run", "ruff", "check", "src", "tests"], "lint (ruff)"),
        (["uv", "run", "ruff", "format", "--check", "src", "tests"], "format (ruff)"),
        (["uv", "run", "basedpyright"], "types (basedpyright)"),
        (["uv", "run", "pytest", "-q"], "tests (pytest)"),
    ]
    results = [(label, run(cmd, label)) for cmd, label in checks]

    smoke = smoke_ui() if app_type == "ui" else smoke_job()
    results.append(("smoke run", smoke))

    print("\n" + "=" * 40 + "\nSUMMARY")
    for label, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    failed = [label for label, ok in results if not ok]
    record(not failed)
    if failed:
        print(f"\n{len(failed)} check(s) failed: {', '.join(failed)}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
