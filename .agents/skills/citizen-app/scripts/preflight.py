#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report local citizen-app capabilities before the interview begins."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Check:
    key: str
    name: str
    command: tuple[str, ...]
    missing_status: str
    failed_status: str
    message: str
    blocking: bool = True


def browser_command() -> tuple[str, ...]:
    configured = os.environ.get("BROWSER")
    if configured:
        return (configured.split()[0],)
    for candidate in ("open", "xdg-open", "cmd.exe"):
        if shutil.which(candidate):
            return (candidate,)
    return ("__citizen_browser_not_found__",)


def planned_checks(provider: str, require_container: bool) -> list[Check]:
    checks = [
        Check(
            "python_project_tools",
            "Python project tools",
            ("uv", "--version"),
            "missing",
            "command_failed",
            "Python project tooling is unavailable.",
        ),
        Check(
            "git",
            "Git",
            ("git", "--version"),
            "missing",
            "command_failed",
            "Version-control tooling is unavailable.",
        ),
        Check(
            "browser",
            "Browser",
            browser_command(),
            "missing",
            "command_failed",
            "A browser is needed later for the citizen-visible dashboard review.",
            blocking=False,
        ),
    ]
    if provider == "github":
        checks.append(
            Check(
                "repository_provider",
                "GitHub sign-in",
                ("gh", "auth", "status"),
                "missing",
                "authentication_missing",
                "GitHub publishing needs a signed-in GitHub CLI session.",
            )
        )
    if require_container:
        checks.append(
            Check(
                "container_engine",
                "Container engine",
                ("docker", "info"),
                "missing",
                "installed_not_ready",
                "Docker is installed but its engine is not ready; start it and retry.",
            )
        )
    return checks


def executable_exists(command: tuple[str, ...]) -> bool:
    return shutil.which(command[0]) is not None


def command_succeeds(command: tuple[str, ...], *, attempts: int = 1) -> bool:
    for attempt in range(attempts):
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result is not None and result.returncode == 0:
            return True
        if attempt + 1 < attempts:
            time.sleep(1)
    return False


def assess_capabilities(
    provider: str,
    container_mode: str | None,
    *,
    exists: Callable[[tuple[str, ...]], bool] = executable_exists,
    succeeds: Callable[..., bool] = command_succeeds,
) -> tuple[dict[str, str], list[tuple[Check, str]]]:
    require_container = container_mode == "local"
    checks = planned_checks(provider, require_container)
    details: list[tuple[Check, str]] = []
    capabilities = {
        "python_project_tools": "unknown",
        "git": "unknown",
        "browser": "unknown",
        "container_engine": "externalized" if container_mode == "external" else "not_required",
        "repository_provider": "local_only" if provider == "local" else "unknown",
    }
    for check in checks:
        if not exists(check.command):
            status = check.missing_status
        elif check.key == "browser":
            status = "ready"
        else:
            attempts = 5 if check.key == "container_engine" else 1
            status = "ready" if succeeds(check.command, attempts=attempts) else check.failed_status
        capabilities[check.key] = status
        details.append((check, status))
    return capabilities, details


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("local", "github"), required=True)
    parser.add_argument("--require-container", action="store_true")
    parser.add_argument("--container-mode", choices=("local", "external"), default=None)
    parser.add_argument("--json", action="store_true", help="emit only structured capability JSON")
    parser.add_argument("--output", type=Path, help="also write structured capability JSON")
    args = parser.parse_args()
    if args.require_container and args.container_mode == "external":
        parser.error("--require-container cannot be combined with --container-mode external")
    mode = args.container_mode or ("local" if args.require_container else None)
    capabilities, details = assess_capabilities(args.provider, mode)
    payload = {"schema_version": 1, "capabilities": capabilities}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for check, status in details:
            label = (
                "PASS" if status == "ready" else "INFO" if not check.blocking else "NEEDS ATTENTION"
            )
            print(f"[{label}] {check.name}: {status}")
        if mode == "external":
            print("[INFO] Container engine: externalized")
        if args.provider == "local":
            print("[INFO] Repository provider: local only")
    blockers = [check for check, status in details if check.blocking and status != "ready"]
    if blockers:
        if not args.json:
            print("\nBefore we start:")
            for check in blockers:
                print(f"- {check.message}")
        return 1
    if not args.json:
        print("\nPreflight passed. The local build can start.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
