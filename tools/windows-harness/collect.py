"""Validate and summarize an evidence directory copied from a Windows run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def collect(evidence_dir: Path) -> dict[str, Any]:
    environment = load_json(evidence_dir / "environment.json")
    summary = load_json(evidence_dir / "summary.json")
    if environment.get("elevated") is not False:
        raise ValueError("run did not prove a standard-user token")
    if summary.get("result") != "passed":
        raise ValueError("scenario did not pass")
    source = evidence_dir / "source.zip"
    result = {
        "schema_version": 1,
        "run_id": environment.get("run_id"),
        "scenario": summary.get("scenario"),
        "windows_build": environment.get("windows_build"),
        "memory_bytes": environment.get("memory_bytes"),
        "standard_user": True,
        "result": summary.get("result"),
        "stage": summary.get("stage"),
        "source_archive": source.name if source.is_file() else None,
        "source_sha256": sha256_file(source) if source.is_file() else None,
    }
    (evidence_dir / "collected.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_dir", type=Path)
    args = parser.parse_args()
    result = collect(args.evidence_dir.resolve())
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
