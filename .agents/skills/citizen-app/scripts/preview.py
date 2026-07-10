#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Execute the current dashboard or job and write human-readable evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

STATE_PATH = Path(".plan/state.json")
DEFAULT_OUTPUT_DIR = Path(".plan/preview")

UI_APP_TEST = r"""
from streamlit.testing.v1 import AppTest

app = AppTest.from_file("src/app/ui.py").run(timeout=30)
if app.exception:
    for exception in app.exception:
        print(f"RENDER ERROR: {exception}")
    raise SystemExit(1)

print("DASHBOARD RENDERED")
print(f"titles: {len(app.title)}")
print(f"buttons: {len(app.button)}")
print(f"text inputs: {len(app.text_input)}")
print(f"select boxes: {len(app.selectbox)}")
print(f"dataframes: {len(app.dataframe)}")
"""


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    return env


def resolve_type(explicit: str | None) -> str:
    if explicit:
        return explicit
    if STATE_PATH.is_file():
        raw = json.loads(STATE_PATH.read_text())
        app_type = raw.get("app_type")
        if app_type in {"ui", "job"}:
            return str(app_type)
    sys.exit("error: app type is unknown; pass --type ui|job or record it in state")


def uv_command(*parts: str, env_path: Path = Path(".env")) -> list[str]:
    command = ["uv", "run"]
    if env_path.is_file():
        command.extend(("--env-file", str(env_path)))
    command.extend(parts)
    return command


def run_and_write(command: list[str], output: Path) -> bool:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=clean_env(),
    )
    text = result.stdout
    if result.stderr:
        text += ("\n" if text else "") + result.stderr
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text.strip() + "\n")
    print(text.strip())
    print(f"\nEvidence: {output}")
    return result.returncode == 0 and bool(text.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--type", choices=("ui", "job"), default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    app_type = resolve_type(args.type)
    if app_type == "ui":
        command = uv_command("python", "-c", UI_APP_TEST)
        output = args.output_dir / "ui-summary.txt"
    else:
        command = uv_command("python", "-m", "app.job", "--dry-run")
        output = args.output_dir / "job-output.txt"

    if not run_and_write(command, output):
        print("Preview failed; fix the application before asking for approval.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
