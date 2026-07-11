#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Perform shell-neutral citizen project creation and starter operations."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parents[1]


def emit(operation: str, **values: Any) -> None:
    print(json.dumps({"schema_version": 1, "operation": operation, **values}))


def run(command: list[str], *, cwd: Path | None = None) -> None:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        if result.stdout.strip():
            print(result.stdout.strip(), file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)


def cmd_create_local(args: argparse.Namespace) -> int:
    source = args.source.resolve()
    destination = args.destination.resolve()
    if destination.exists():
        if (destination / ".git").is_dir() and (destination / "pyproject.toml").is_file():
            emit("create-local", result="already_exists", destination=str(destination))
            return 0
        sys.exit(f"error: destination exists but is not an adopted project: {destination}")
    run(["git", "clone", "--no-hardlinks", str(source), str(destination)])
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=destination,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if remote.returncode == 0:
        run(["git", "remote", "remove", "origin"], cwd=destination)
    emit("create-local", result="created", name=args.name, destination=str(destination))
    return 0


def command_output(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(result.returncode)
    return result.stdout.strip()


def cmd_create_github(args: argparse.Namespace) -> int:
    destination = args.destination.resolve()
    if destination.exists():
        if (destination / ".git").is_dir() and (destination / "pyproject.toml").is_file():
            emit("create-github", result="already_exists", destination=str(destination))
            return 0
        sys.exit(f"error: destination exists but is not an adopted project: {destination}")
    template = command_output(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]
    )
    owner = command_output(["gh", "api", "user", "--jq", ".login"])
    repository = f"{owner}/{args.name}"
    run(["gh", "repo", "create", repository, "--template", template, "--private"])
    populated = False
    for _ in range(5):
        check = subprocess.run(
            ["gh", "api", f"repos/{repository}/contents/pyproject.toml"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if check.returncode == 0:
            populated = True
            break
        time.sleep(2)
    if not populated:
        sys.exit("error: GitHub created the repository but template population did not finish")
    run(["git", "clone", f"https://github.com/{repository}.git", str(destination)])
    if not (destination / "pyproject.toml").is_file():
        sys.exit("error: the cloned repository is missing pyproject.toml")
    emit(
        "create-github",
        result="created",
        destination=str(destination),
        repository=repository,
        url=f"https://github.com/{repository}",
    )
    return 0


def cmd_inspect(_: argparse.Namespace) -> int:
    remote = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    emit(
        "inspect",
        result="ready",
        path=str(Path.cwd().resolve()),
        name=Path.cwd().name,
        has_state=Path(".plan/state.json").is_file(),
        is_application=Path(".plan/state.json").is_file() or Path.cwd().name.startswith("citizen-"),
        remote_url=remote.stdout.strip() if remote.returncode == 0 else None,
    )
    return 0


def copy_idempotent(source: Path, destination: Path) -> str:
    if destination.is_file():
        if destination.read_bytes() == source.read_bytes():
            return "unchanged"
        sys.exit(
            f"error: {destination} already contains application work; "
            "rewind deliberately or pass --force to replace it"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return "created"


def cmd_apply_starter(args: argparse.Namespace) -> int:
    mapping = {
        "ui": {
            "ui-streamlit/core.py.template": Path("src/app/core.py"),
            "ui-streamlit/ui.py.template": Path("src/app/ui.py"),
            "ui-streamlit/present.py.template": Path("src/app/present.py"),
        },
        "job": {
            "job-cronjob/core.py.template": Path("src/app/core.py"),
            "job-cronjob/job.py.template": Path("src/app/job.py"),
        },
    }
    results: dict[str, str] = {}
    for relative, destination in mapping[args.type].items():
        source = SKILL_DIR / "assets" / relative
        if args.force:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            results[destination.as_posix()] = "replaced"
        else:
            results[destination.as_posix()] = copy_idempotent(source, destination)
    if args.type == "ui" and not args.skip_dependencies:
        run(["uv", "add", "streamlit", "pandas"])
    emit("apply-starter", result="ready", app_type=args.type, files=results)
    return 0


def replace_project_name(text: str, name: str) -> str:
    section = re.search(r"(?ms)^\[project\]\s*$.*?(?=^\[|\Z)", text)
    if section is None:
        sys.exit("error: pyproject.toml has no [project] section")
    block = section.group(0)
    updated, count = re.subn(r'(?m)^name\s*=\s*"[^"]*"\s*$', f'name = "{name}"', block)
    if count != 1:
        sys.exit("error: [project] must contain exactly one quoted name")
    return text[: section.start()] + updated + text[section.end() :]


def cmd_set_identity(args: argparse.Namespace) -> int:
    path = Path("pyproject.toml")
    original = path.read_text(encoding="utf-8")
    updated = replace_project_name(original, args.name)
    changed = updated != original
    if changed:
        path.write_text(updated, encoding="utf-8")
    if not args.skip_lock:
        run(["uv", "lock"])
    emit("set-identity", result="updated" if changed else "unchanged", name=args.name)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-local")
    create.add_argument("--name", required=True)
    create.add_argument("--destination", type=Path, required=True)
    create.add_argument("--source", type=Path, default=Path.cwd())
    create.set_defaults(func=cmd_create_local)
    github = sub.add_parser("create-github")
    github.add_argument("--name", required=True)
    github.add_argument("--destination", type=Path, required=True)
    github.set_defaults(func=cmd_create_github)
    sub.add_parser("inspect").set_defaults(func=cmd_inspect)
    starter = sub.add_parser("apply-starter")
    starter.add_argument("--type", choices=("ui", "job"), required=True)
    starter.add_argument("--force", action="store_true")
    starter.add_argument("--skip-dependencies", action="store_true", help=argparse.SUPPRESS)
    starter.set_defaults(func=cmd_apply_starter)
    identity = sub.add_parser("set-identity")
    identity.add_argument("--name", required=True)
    identity.add_argument("--skip-lock", action="store_true", help=argparse.SUPPRESS)
    identity.set_defaults(func=cmd_set_identity)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
