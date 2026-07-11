#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Execute the current dashboard or job and write structured preview evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STATE_PATH = Path(".plan/state.json")
DEFAULT_OUTPUT_DIR = Path(".plan/preview")

UI_APP_TEST = r"""
import json
from streamlit.testing.v1 import AppTest

app = AppTest.from_file("src/app/ui.py").run(timeout=30)
if app.exception:
    for exception in app.exception:
        print(f"RENDER ERROR: {exception}")
    raise SystemExit(1)

def count(name):
    try:
        return len(app.get(name))
    except Exception:
        return 0

summary = {
    "titles": count("title"),
    "headings": count("header") + count("subheader"),
    "text_inputs": count("text_input"),
    "number_inputs": count("number_input"),
    "date_inputs": count("date_input"),
    "select_boxes": count("selectbox"),
    "multiselects": count("multiselect"),
    "buttons": count("button"),
    "toggles": count("toggle") + count("checkbox"),
    "metrics": count("metric"),
    "tables": count("table") + count("dataframe"),
    "charts": sum(count(name) for name in (
        "bar_chart", "line_chart", "area_chart", "scatter_chart", "vega_lite_chart"
    )),
    "warnings": count("warning"),
    "errors": count("error"),
    "empty_states": count("info"),
    "exceptions": len(app.exception),
}
print("DASHBOARD RENDERED")
print("EVIDENCE_JSON:" + json.dumps(summary, sort_keys=True))
"""


def clean_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    return env


def resolve_type(explicit: str | None) -> str:
    if explicit:
        return explicit
    if STATE_PATH.is_file():
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
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
        encoding="utf-8",
        errors="replace",
        check=False,
        env=clean_env(),
    )
    text = result.stdout
    if result.stderr:
        diagnostics = output.with_suffix(".stderr.txt")
        diagnostics.parent.mkdir(parents=True, exist_ok=True)
        diagnostics.write_text(result.stderr.strip() + "\n", encoding="utf-8")
        print(result.stderr.strip(), file=sys.stderr)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text.strip() + "\n", encoding="utf-8")
    print(text.strip())
    print(f"\nEvidence: {output}")
    return result.returncode == 0 and bool(text.strip())


def optional_assertions() -> tuple[bool, dict[str, Any]]:
    path = Path("tests/preview_assertions.py")
    if not path.is_file():
        return True, {"file": None, "passed": True, "output": ""}
    result = subprocess.run(
        uv_command("python", str(path)),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        env=clean_env(),
    )
    return result.returncode == 0, {
        "file": path.as_posix(),
        "passed": result.returncode == 0,
        "output": result.stdout,
        "diagnostics": result.stderr,
    }


def write_structured(
    output_dir: Path, app_type: str, human_output: Path, passed: bool, details: dict[str, Any]
) -> Path:
    assertion_passed, assertions = optional_assertions()
    payload = {
        "schema_version": 1,
        "run_at": datetime.now(UTC).isoformat(),
        "app_type": app_type,
        "render_passed": passed and assertion_passed,
        "human_summary": human_output.as_posix(),
        "details": details,
        "acceptance_assertions": assertions,
    }
    path = output_dir / "summary.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


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
    passed = run_and_write(command, output)
    details: dict[str, Any] = {"output": output.read_text(encoding="utf-8").strip()}
    if app_type == "ui" and "EVIDENCE_JSON:" in details["output"]:
        raw = details["output"].split("EVIDENCE_JSON:", 1)[1].splitlines()[0]
        details = json.loads(raw)
    evidence = write_structured(args.output_dir, app_type, output, passed, details)
    if not passed or not json.loads(evidence.read_text(encoding="utf-8"))["render_passed"]:
        print("Preview failed; fix the application before asking for approval.", file=sys.stderr)
        return 1
    print(f"Structured evidence: {evidence}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
