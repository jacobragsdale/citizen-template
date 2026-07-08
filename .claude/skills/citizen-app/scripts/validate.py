#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Fail-hard validation gate for a citizen app.

Runs the same checks for every app, plus a type-specific smoke run that proves
the app actually boots. Any failure => nonzero exit and a plain report of what
broke. The build stage loops back here until this exits 0.

App type is read from .plan/state.json unless --type is given.

  uv run .claude/skills/citizen-app/scripts/validate.py
  uv run .claude/skills/citizen-app/scripts/validate.py --type ui
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

STATE_PATH = Path(".plan/state.json")
UI_SMOKE_PORT = 8599  # unlikely to collide with a real Streamlit dev server (8501)


def run(cmd: list[str], label: str) -> bool:
    print(f"\n=== {label}: {' '.join(cmd)} ===")
    result = subprocess.run(cmd)
    ok = result.returncode == 0
    print(f"--- {label}: {'PASS' if ok else 'FAIL'}")
    return ok


def smoke_job() -> bool:
    return run(["uv", "run", "python", "-m", "app.job", "--dry-run"], "smoke (job dry-run)")


def smoke_ui() -> bool:
    print("\n=== smoke (streamlit boots): starting headless server ===")
    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "streamlit",
            "run",
            "src/app/ui.py",
            "--server.headless=true",
            f"--server.port={UI_SMOKE_PORT}",
            "--server.address=127.0.0.1",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    health = f"http://127.0.0.1:{UI_SMOKE_PORT}/_stcore/health"
    try:
        for _ in range(30):  # ~30s: cold uv-run + streamlit startup
            if proc.poll() is not None:
                print("--- smoke (ui): FAIL — server exited during startup")
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--type", choices=["ui", "job"], default=None)
    args = parser.parse_args()
    app_type = resolve_type(args.type)

    checks = [
        (["uv", "sync", "--quiet"], "install deps (uv sync)"),
        (["uv", "run", "ruff", "check", "."], "lint (ruff)"),
        (["uv", "run", "ruff", "format", "--check", "."], "format (ruff)"),
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
    if failed:
        print(f"\n{len(failed)} check(s) failed: {', '.join(failed)}")
        return 1
    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
