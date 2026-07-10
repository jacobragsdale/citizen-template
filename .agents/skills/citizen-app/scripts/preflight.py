#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check local prerequisites before starting a citizen-app build."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    name: str
    command: tuple[str, ...]
    missing_message: str


def planned_checks(provider: str, require_container: bool) -> list[Check]:
    checks = [
        Check("uv", ("uv", "--version"), "Python project tooling is unavailable."),
        Check("git", ("git", "--version"), "Version-control tooling is unavailable."),
    ]
    if provider == "github":
        checks.append(
            Check(
                "GitHub sign-in",
                ("gh", "auth", "status"),
                "GitHub publishing needs a signed-in GitHub CLI session.",
            )
        )
    if require_container:
        checks.append(
            Check(
                "Docker",
                ("docker", "info"),
                "The container handoff needs Docker installed and running.",
            )
        )
    return checks


def executable_exists(command: tuple[str, ...]) -> bool:
    return shutil.which(command[0]) is not None


def command_succeeds(command: tuple[str, ...]) -> bool:
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def assess(
    checks: list[Check],
    *,
    exists: Callable[[tuple[str, ...]], bool] = executable_exists,
    succeeds: Callable[[tuple[str, ...]], bool] = command_succeeds,
) -> list[tuple[Check, bool]]:
    return [(check, exists(check.command) and succeeds(check.command)) for check in checks]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=("local", "github"), required=True)
    parser.add_argument(
        "--require-container",
        action="store_true",
        help="require an available Docker daemon for the final local image gate",
    )
    args = parser.parse_args()

    results = assess(planned_checks(args.provider, args.require_container))
    failures = []
    for check, passed in results:
        print(f"[{'PASS' if passed else 'NEEDS ATTENTION'}] {check.name}")
        if not passed:
            failures.append(check.missing_message)

    if failures:
        print("\nBefore we start:")
        for message in failures:
            print(f"- {message}")
        return 1

    print("\nPreflight passed. The local build can start.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
