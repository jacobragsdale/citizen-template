#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build an image, run its type-specific smoke check, and write bound evidence."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import state as workflow_state

DEFAULT_EVIDENCE = Path(".plan/container/verification.json")


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def smoke_job(tag: str) -> tuple[bool, dict[str, Any]]:
    result = run(["docker", "run", "--rm", tag], capture=True)
    return result.returncode == 0 and bool(result.stdout.strip()), {
        "kind": "job",
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def smoke_ui(tag: str) -> tuple[bool, dict[str, Any]]:
    port = free_port()
    name = f"citizen-smoke-{int(time.time())}"
    started = run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            name,
            "-p",
            f"127.0.0.1:{port}:8501",
            tag,
        ],
        capture=True,
    )
    if started.returncode != 0:
        return False, {
            "kind": "ui",
            "exit_code": started.returncode,
            "stdout": started.stdout,
            "stderr": started.stderr,
        }
    health = f"http://127.0.0.1:{port}/_stcore/health"
    passed = False
    try:
        for _ in range(45):
            try:
                with urllib.request.urlopen(health, timeout=1) as response:
                    if response.status == 200 and response.read().strip() == b"ok":
                        passed = True
                        break
            except (OSError, TimeoutError):
                time.sleep(1)
        logs = run(["docker", "logs", name], capture=True)
        return passed, {
            "kind": "ui",
            "health_url": health,
            "exit_code": 0 if passed else 1,
            "stdout": logs.stdout,
            "stderr": logs.stderr,
        }
    finally:
        run(["docker", "stop", "--time", "10", name], capture=True)


def write_evidence(
    path: Path,
    *,
    tag: str,
    image_id: str,
    runtime_passed: bool,
    runtime: dict[str, Any],
) -> None:
    payload = {
        "schema_version": 1,
        "run_at": datetime.now(UTC).isoformat(),
        "result": "passed" if runtime_passed else "failed",
        "runtime_passed": runtime_passed,
        "project_fingerprint": workflow_state.project_fingerprint(),
        "dockerfile_fingerprint": workflow_state.dockerfile_fingerprint(),
        "tag": tag,
        "image_id": image_id,
        "runtime": runtime,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default=f"{Path.cwd().name.lower()}:local")
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--no-record", action="store_true")
    args = parser.parse_args()

    state = workflow_state.load()
    if state.get("app_type") not in {"ui", "job"}:
        print("error: application type is missing from workflow state", file=sys.stderr)
        return 1
    if not Path("Dockerfile").is_file():
        print("error: Dockerfile is missing", file=sys.stderr)
        return 1

    built = run(["docker", "build", "-t", args.tag, "."])
    if built.returncode != 0:
        return built.returncode
    inspected = run(["docker", "image", "inspect", args.tag, "--format", "{{.Id}}"], capture=True)
    image_id = inspected.stdout.strip()
    if inspected.returncode != 0 or not image_id.startswith("sha256:"):
        print("error: built image could not be inspected", file=sys.stderr)
        return 1

    if state["app_type"] == "ui":
        passed, runtime = smoke_ui(args.tag)
    else:
        passed, runtime = smoke_job(args.tag)
    write_evidence(
        args.evidence,
        tag=args.tag,
        image_id=image_id,
        runtime_passed=passed,
        runtime=runtime,
    )
    print(f"[{'PASS' if passed else 'FAIL'}] container runtime")
    print(f"Evidence: {args.evidence}")
    if not passed:
        return 1
    if args.no_record:
        return 0
    recorded = run(
        [
            sys.executable,
            str(Path(__file__).with_name("state.py")),
            "record-container-verification",
            "--evidence",
            str(args.evidence),
        ]
    )
    return recorded.returncode


if __name__ == "__main__":
    raise SystemExit(main())
