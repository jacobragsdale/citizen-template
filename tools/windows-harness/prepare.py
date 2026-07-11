"""Prepare a checksum-bound, no-admin Windows harness payload."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

HARNESS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HARNESS_DIR.parents[1]
TOOL_MANIFEST = HARNESS_DIR / "tool-manifest.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_tool_manifest(path: Path = TOOL_MANIFEST) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("tools"), list):
        raise ValueError("tool manifest has an unsupported schema")
    for tool in payload["tools"]:
        required = {"name", "version", "filename", "url", "sha256"}
        if not isinstance(tool, dict) or not required.issubset(tool):
            raise ValueError("tool manifest contains an incomplete entry")
    return payload


def download_tool(tool: dict[str, str], destination: Path, cache_dir: Path) -> Path:
    cached = cache_dir / tool["filename"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    if not cached.is_file() or sha256_file(cached) != tool["sha256"]:
        temporary = cached.with_suffix(cached.suffix + ".partial")
        with (
            urllib.request.urlopen(tool["url"], timeout=60) as response,
            temporary.open("wb") as target,
        ):
            shutil.copyfileobj(response, target)
        if sha256_file(temporary) != tool["sha256"]:
            temporary.unlink(missing_ok=True)
            raise ValueError(f"checksum mismatch for {tool['name']}")
        temporary.replace(cached)
    output = destination / tool["filename"]
    shutil.copy2(cached, output)
    return output


def repository_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=True,
    )
    files = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        relative = Path(raw.decode("utf-8"))
        if relative.parts and relative.parts[0] in {".test-runs", ".venv"}:
            continue
        path = REPO_ROOT / relative
        if path.is_file():
            files.append(relative)
    return sorted(files, key=lambda item: item.as_posix())


def write_source_archive(destination: Path) -> Path:
    archive = destination / "template-source.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for relative in repository_files():
            output.write(REPO_ROOT / relative, relative.as_posix())
    return archive


def prepare_wheelhouse(destination: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix="citizen-wheelhouse-") as raw_temp:
        temporary = Path(raw_temp)
        requirements = temporary / "requirements.txt"
        subprocess.run(
            [
                "uv",
                "export",
                "--all-groups",
                "--no-emit-project",
                "--no-hashes",
                "--output-file",
                str(requirements),
            ],
            cwd=REPO_ROOT,
            check=True,
        )
        wheelhouse = temporary / "wheelhouse"
        wheelhouse.mkdir()
        subprocess.run(
            [
                "uvx",
                "--from",
                "pip",
                "pip",
                "download",
                "--requirement",
                str(requirements),
                "--dest",
                str(wheelhouse),
                "--only-binary=:all:",
                "--platform",
                "win_amd64",
                "--python-version",
                "3.11",
                "--implementation",
                "cp",
                "streamlit",
                "pandas",
                # pip evaluates environment markers on the Mac controller even
                # when downloading Windows wheels, so name Windows-only roots.
                "colorama",
                # Build-system requirements are intentionally absent from
                # `uv export --no-emit-project` but are required offline.
                "hatchling",
                "editables",
                "tzdata",
                "watchdog",
                "tomli",
            ],
            check=True,
        )
        archive = destination / "wheelhouse.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
            output.write(requirements, "requirements.txt")
            for wheel in sorted(wheelhouse.iterdir()):
                output.write(wheel, wheel.name)
        return archive


def prepare_ui_resolution(destination: Path) -> tuple[Path, Path]:
    with tempfile.TemporaryDirectory(prefix="citizen-ui-lock-") as raw_temp:
        project = Path(raw_temp)
        shutil.copy2(REPO_ROOT / "pyproject.toml", project / "pyproject.toml")
        shutil.copy2(REPO_ROOT / "uv.lock", project / "uv.lock")
        subprocess.run(
            [
                "uv",
                "add",
                "--project",
                str(project),
                "--no-sync",
                "streamlit",
                "pandas",
            ],
            check=True,
        )
        target = destination / "ui-uv.lock"
        shutil.copy2(project / "uv.lock", target)
        project_target = destination / "ui-pyproject.toml"
        shutil.copy2(project / "pyproject.toml", project_target)
        return project_target, target


def git_revision() -> dict[str, Any]:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
    )
    return {"commit": commit, "working_tree_dirty": dirty}


def prepare_payload(output: Path, cache_dir: Path, *, include_wheelhouse: bool) -> Path:
    if output.exists():
        raise FileExistsError(f"payload destination already exists: {output}")
    output.mkdir(parents=True)
    manifest = load_tool_manifest()
    artifacts: list[dict[str, Any]] = []
    for tool in manifest["tools"]:
        path = download_tool(tool, output, cache_dir)
        artifacts.append(
            {
                "name": tool["name"],
                "filename": path.name,
                "version": tool["version"],
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    source = write_source_archive(output)
    artifacts.append(
        {
            "name": "template-source",
            "filename": source.name,
            "sha256": sha256_file(source),
            "bytes": source.stat().st_size,
        }
    )
    if include_wheelhouse:
        wheelhouse = prepare_wheelhouse(output)
        artifacts.append(
            {
                "name": "wheelhouse",
                "filename": wheelhouse.name,
                "sha256": sha256_file(wheelhouse),
                "bytes": wheelhouse.stat().st_size,
            }
        )
        ui_project, ui_lock = prepare_ui_resolution(output)
        for name, path in (("ui-project", ui_project), ("ui-lock", ui_lock)):
            artifacts.append(
                {
                    "name": name,
                    "filename": path.name,
                    "sha256": sha256_file(path),
                    "bytes": path.stat().st_size,
                }
            )
    for script_name in ("bootstrap.ps1", "run-scenario.ps1"):
        source_script = HARNESS_DIR / script_name
        target = output / script_name
        shutil.copy2(source_script, target)
        artifacts.append(
            {
                "name": script_name.removesuffix(".ps1"),
                "filename": target.name,
                "sha256": sha256_file(target),
                "bytes": target.stat().st_size,
            }
        )
    payload = {
        "schema_version": 1,
        "source": git_revision(),
        "artifacts": artifacts,
    }
    manifest_path = output / "payload-manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache/citizen-windows-harness",
    )
    parser.add_argument("--skip-wheelhouse", action="store_true")
    args = parser.parse_args()
    manifest = prepare_payload(
        args.output.resolve(), args.cache_dir.resolve(), include_wheelhouse=not args.skip_wheelhouse
    )
    print(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
