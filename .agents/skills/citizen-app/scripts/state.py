#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Own the citizen-app workflow state, evidence, and stage transitions.

State lives in .plan/state.json. This script is the only supported writer.
Generic ``set`` is intentionally restricted and can never change ``stage``.
Evidence commands fingerprint the approved plan and application revision so
later edits cannot silently reuse stale approvals or check results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STATE_PATH = Path(".plan/state.json")
PLAN_PATH = Path(".plan/PLAN.md")
STATE_VERSION = 2

STAGES = [
    "scaffold",
    "choose-type",
    "interview",
    "plan-review",
    "build",
    "preview",
    "user-review",
    "validate",
    "containerize",
    "ship",
    "done",
]

INITIAL: dict[str, Any] = {
    "version": STATE_VERSION,
    "stage": "scaffold",
    "app_name": None,
    "app_type": None,
    "workspace_ready": False,
    "repo_provider": None,
    "repo_visibility": None,
    "repo_url": None,
    "requirements": {},
    "plan": {"approved": False, "fingerprint": None},
    "build": {"recorded": False, "fingerprint": None},
    "preview": {
        "passed": False,
        "approved": False,
        "evidence": None,
        "evidence_fingerprint": None,
        "fingerprint": None,
    },
    "validation": {
        "passed": False,
        "last_run": None,
        "evidence": None,
        "evidence_fingerprint": None,
        "fingerprint": None,
    },
    "container": {
        "required": True,
        "image_built": False,
        "tag": None,
        "image_id": None,
        "fingerprint": None,
    },
    "pr_url": None,
}

SETTABLE_FIELDS = {
    "workspace_ready",
    "repo_provider",
    "repo_visibility",
    "repo_url",
    "app_type",
    "requirements",
    "container.required",
}

PROJECT_FILES = (
    Path(".plan/PLAN.md"),
    Path(".env.example"),
    Path("README.md"),
    Path("pyproject.toml"),
    Path("uv.lock"),
)


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def deep_merge(default: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(default)
    for key, value in current.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def normalize_state(raw: dict[str, Any]) -> dict[str, Any]:
    """Load current state and safely adapt the original workflow schema."""
    if raw.get("version") == STATE_VERSION:
        state = deep_merge(INITIAL, raw)
    else:
        state = deepcopy(INITIAL)
        for key in ("app_name", "app_type", "repo_url", "requirements"):
            if key in raw:
                state[key] = raw[key]

        old_stage = raw.get("stage", "scaffold")
        state["workspace_ready"] = old_stage != "scaffold" or bool(raw.get("repo_url"))
        state["repo_provider"] = "github" if raw.get("repo_url") else "local"
        state["repo_visibility"] = "private" if raw.get("repo_url") else "local"
        if raw.get("plan_approved"):
            state["plan"]["approved"] = True
        if raw.get("image_built"):
            state["container"]["image_built"] = True

        # Original runs at or past build lack plan fingerprints and working-result
        # approval. Rewind them to reapprove the plan before recording the build.
        if old_stage in {"build", "validate", "containerize", "ship", "done"}:
            state["stage"] = "plan-review"
        elif old_stage in STAGES:
            state["stage"] = old_stage

    state["version"] = STATE_VERSION
    if state.get("stage") not in STAGES:
        sys.exit(f"error: unknown workflow stage {state.get('stage')!r}")
    return state


def load() -> dict[str, Any]:
    if not STATE_PATH.exists():
        sys.exit("error: no .plan/state.json — start with the scaffold playbook")
    try:
        raw = json.loads(STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"error: cannot read {STATE_PATH}: {exc}") from exc
    if not isinstance(raw, dict):
        sys.exit(f"error: {STATE_PATH} must contain a JSON object")
    return normalize_state(raw)


def save(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def dotted_get(state: dict[str, Any], key: str) -> Any:
    node: Any = state
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            sys.exit(f"error: no such field {key!r}")
        node = node[part]
    return node


def dotted_set(state: dict[str, Any], key: str, value: Any) -> None:
    parts = key.split(".")
    node: dict[str, Any] = state
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            sys.exit(f"error: {key!r} is not a writable nested field")
        node = child
    node[parts[-1]] = value


def existing_file_fingerprint(path: Path) -> str | None:
    if not path.is_file():
        return None
    contents = path.read_bytes()
    if not contents.strip():
        return None
    return hashlib.sha256(contents).hexdigest()


def file_fingerprint(path: Path) -> str:
    fingerprint = existing_file_fingerprint(path)
    if fingerprint is None:
        sys.exit(f"error: required evidence file is missing or empty: {path}")
    return fingerprint


def iter_project_files() -> list[Path]:
    files = [path for path in PROJECT_FILES if path.is_file()]
    for root in (Path("src"), Path("tests")):
        if root.is_dir():
            files.extend(path for path in root.rglob("*") if path.is_file())
    return sorted(set(files), key=lambda path: path.as_posix())


def project_fingerprint() -> str:
    digest = hashlib.sha256()
    files = iter_project_files()
    if not files:
        sys.exit("error: no project files found to fingerprint")
    for path in files:
        digest.update(path.as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def container_fingerprint() -> str:
    dockerfile = Path("Dockerfile")
    if not dockerfile.is_file():
        sys.exit("error: Dockerfile is missing")
    digest = hashlib.sha256()
    digest.update(project_fingerprint().encode())
    digest.update(dockerfile.read_bytes())
    return digest.hexdigest()


def valid_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and parsed.path not in {"", "/"}


def requirements_complete(state: dict[str, Any]) -> bool:
    requirements = state.get("requirements")
    if not isinstance(requirements, dict):
        return False
    goal = requirements.get("goal")
    criteria = requirements.get("acceptance_criteria")
    return (
        isinstance(goal, str)
        and bool(goal.strip())
        and isinstance(criteria, list)
        and 1 <= len(criteria) <= 12
        and all(isinstance(item, str) and item.strip() for item in criteria)
    )


def plan_current(state: dict[str, Any]) -> bool:
    stored = dotted_get(state, "plan.fingerprint")
    current = existing_file_fingerprint(PLAN_PATH)
    return bool(stored) and current is not None and stored == current


def project_current(state: dict[str, Any], field: str) -> bool:
    stored = dotted_get(state, field)
    return bool(stored) and stored == project_fingerprint()


def evidence_current(state: dict[str, Any], section: str) -> bool:
    raw_path = dotted_get(state, f"{section}.evidence")
    stored = dotted_get(state, f"{section}.evidence_fingerprint")
    if not isinstance(raw_path, str) or not stored:
        return False
    return existing_file_fingerprint(Path(raw_path)) == stored


def container_current(state: dict[str, Any]) -> bool:
    stored = dotted_get(state, "container.fingerprint")
    return bool(stored) and Path("Dockerfile").is_file() and stored == container_fingerprint()


def reset_from(state: dict[str, Any], target: str) -> None:
    target_index = STAGES.index(target)
    if target_index <= STAGES.index("choose-type"):
        state["requirements"] = {}
    if target_index <= STAGES.index("plan-review"):
        state["plan"] = deepcopy(INITIAL["plan"])
    if target_index <= STAGES.index("build"):
        state["build"] = deepcopy(INITIAL["build"])
    if target_index <= STAGES.index("preview"):
        state["preview"] = deepcopy(INITIAL["preview"])
    elif target_index <= STAGES.index("user-review"):
        state["preview"]["approved"] = False
    if target_index <= STAGES.index("validate"):
        state["validation"] = deepcopy(INITIAL["validation"])
    if target_index <= STAGES.index("containerize"):
        required = bool(state["container"].get("required", True))
        state["container"] = deepcopy(INITIAL["container"])
        state["container"]["required"] = required
    if target_index <= STAGES.index("ship"):
        state["pr_url"] = None

    if STAGES.index(state["stage"]) > target_index:
        state["stage"] = target


def ensure_stage(state: dict[str, Any], expected: str) -> None:
    if state["stage"] != expected:
        current = state["stage"]
        sys.exit(f"error: this command requires stage {expected!r}; current stage is {current!r}")


def prior_delivery_evidence_current(state: dict[str, Any]) -> str | None:
    if not plan_current(state):
        return "the approved plan changed; rewind to plan-review"
    if (
        not project_current(state, "preview.fingerprint")
        or not evidence_current(state, "preview")
        or not state["preview"]["approved"]
    ):
        return "the approved preview is missing or stale; rewind to preview"
    if (
        not project_current(state, "validation.fingerprint")
        or not evidence_current(state, "validation")
        or not state["validation"]["passed"]
    ):
        return "validation is missing or stale; rewind to validate"
    if state["container"]["required"] and (
        not state["container"]["image_built"] or not container_current(state)
    ):
        return "the required container result is missing or stale; rewind to containerize"
    return None


def gate_failure(state: dict[str, Any], stage: str) -> str | None:
    if stage == "scaffold":
        if not state["workspace_ready"]:
            return "the working repository and preflight are not recorded"
        if state["repo_provider"] not in {
            "local",
            "github",
            "github-enterprise",
            "azure-devops",
        }:
            return "the repository provider is not recorded"
        if state["repo_visibility"] not in {"local", "private", "internal", "public"}:
            return "the repository visibility is not recorded"
        if state["repo_provider"] != "local" and not state["repo_url"]:
            return "the remote repository URL is not recorded"
    elif stage == "choose-type":
        if state["app_type"] not in {"ui", "job"}:
            return "dashboard versus automated-job choice is not recorded"
    elif stage == "interview":
        if not requirements_complete(state) or not PLAN_PATH.is_file():
            return "the plan, goal, and acceptance criteria are incomplete"
    elif stage == "plan-review":
        if not state["plan"]["approved"] or not plan_current(state):
            return "the citizen has not approved the current plan"
    elif stage == "build":
        if not state["build"]["recorded"] or not project_current(state, "build.fingerprint"):
            return "the current build has not been recorded"
    elif stage == "preview":
        if (
            not state["preview"]["passed"]
            or not project_current(state, "preview.fingerprint")
            or not evidence_current(state, "preview")
        ):
            return "executable preview evidence is missing or stale"
    elif stage == "user-review":
        if (
            not state["preview"]["approved"]
            or not project_current(state, "preview.fingerprint")
            or not evidence_current(state, "preview")
        ):
            return "the citizen has not approved the current working preview"
    elif stage == "validate":
        if (
            not state["validation"]["passed"]
            or not project_current(state, "validation.fingerprint")
            or not evidence_current(state, "validation")
        ):
            return "validation evidence is missing or stale"
    elif stage == "containerize" and state["container"]["required"]:
        if not state["container"]["image_built"] or not container_current(state):
            return "the required local container image has not been recorded"
    elif stage == "ship":
        prior_failure = prior_delivery_evidence_current(state)
        if prior_failure:
            return prior_failure
        if not valid_url(state["pr_url"]):
            return "a real HTTPS pull-request URL has not been recorded"
    return None


def cmd_init(args: argparse.Namespace) -> int:
    if STATE_PATH.exists():
        state = load()
        print(f"{STATE_PATH} already exists — resuming at {state['stage']!r}")
        return 0
    state = deepcopy(INITIAL)
    state["app_name"] = args.name
    save(state)
    print(f"Started {args.name!r}. Next: scaffold the working repository.")
    return 0


def cmd_stage(_: argparse.Namespace) -> int:
    print(load()["stage"])
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    if not STATE_PATH.exists():
        print("No saved workflow yet — start with the scaffold stage.")
        return 0
    state = load()
    if args.json:
        print(json.dumps(state, indent=2))
        return 0
    index = STAGES.index(state["stage"])
    app_name = state["app_name"] or "Citizen app"
    print(f"{app_name}: stage {index + 1} of {len(STAGES)} — {state['stage']}")
    failure = gate_failure(state, state["stage"])
    if failure:
        print(f"Next gate: {failure}.")
    elif state["stage"] == "done":
        print(
            "The pull request is ready for the internal delivery pipeline; "
            "deployment is not verified."
        )
    else:
        print("This stage is ready to advance.")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    value = dotted_get(load(), args.key)
    print(value if not isinstance(value, dict | list) else json.dumps(value))
    return 0


def validate_set_value(key: str, value: Any) -> None:
    if key == "workspace_ready" and not isinstance(value, bool):
        sys.exit("error: workspace_ready must be true or false")
    if key == "app_type" and value not in {"ui", "job"}:
        sys.exit("error: app_type must be 'ui' or 'job'")
    if key == "repo_provider" and value not in {
        "local",
        "github",
        "github-enterprise",
        "azure-devops",
    }:
        sys.exit("error: unsupported repo_provider")
    if key == "repo_visibility" and value not in {"local", "private", "internal", "public"}:
        sys.exit("error: unsupported repo_visibility")
    if key == "repo_url" and value is not None and not isinstance(value, str):
        sys.exit("error: repo_url must be a string or null")
    if key == "requirements" and not isinstance(value, dict):
        sys.exit("error: requirements must be a JSON object")
    if key == "container.required" and not isinstance(value, bool):
        sys.exit("error: container.required must be true or false")


def cmd_set(args: argparse.Namespace) -> int:
    if args.key not in SETTABLE_FIELDS:
        allowed = ", ".join(sorted(SETTABLE_FIELDS))
        sys.exit(f"error: {args.key!r} cannot be set directly; allowed fields: {allowed}")
    state = load()
    try:
        value: Any = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    validate_set_value(args.key, value)
    dotted_set(state, args.key, value)

    if args.key == "app_type":
        reset_from(state, "choose-type")
    elif args.key == "requirements":
        reset_from(state, "interview")
    elif args.key == "container.required":
        reset_from(state, "containerize")

    save(state)
    print(f"Recorded {args.key}.")
    return 0


def cmd_rewind(args: argparse.Namespace) -> int:
    state = load()
    target = args.stage
    if STAGES.index(target) > STAGES.index(state["stage"]):
        sys.exit("error: rewind cannot move the workflow forward")
    reset_from(state, target)
    state["stage"] = target
    save(state)
    print(f"Rewound to {target!r}; later approvals and evidence were cleared.")
    return 0


def cmd_approve_plan(_: argparse.Namespace) -> int:
    state = load()
    ensure_stage(state, "plan-review")
    if not requirements_complete(state):
        sys.exit("error: goal and acceptance criteria must be complete before approval")
    state["plan"] = {"approved": True, "fingerprint": file_fingerprint(PLAN_PATH)}
    reset_from(state, "build")
    save(state)
    print("Approved the current plan fingerprint.")
    return 0


def build_files_ready(state: dict[str, Any]) -> str | None:
    app_type = state["app_type"]
    entrypoint = Path("src/app/ui.py" if app_type == "ui" else "src/app/job.py")
    core = Path("src/app/core.py")
    if not entrypoint.is_file() or not core.is_file():
        return "src/app/core.py and the type-specific entry point must exist"
    contents = entrypoint.read_text() + core.read_text()
    if "APP_TITLE" in contents or "APP_DESCRIPTION" in contents:
        return "starter placeholders remain in the application"
    behavior_tests = [
        path for path in Path("tests").glob("test_*.py") if path.name != "test_smoke.py"
    ]
    if not behavior_tests:
        return "at least one behavior test beyond the template smoke test is required"
    return None


def cmd_record_build(_: argparse.Namespace) -> int:
    state = load()
    ensure_stage(state, "build")
    if not state["plan"]["approved"] or not plan_current(state):
        sys.exit("error: the approved plan is missing or stale")
    failure = build_files_ready(state)
    if failure:
        sys.exit(f"error: {failure}")
    state["build"] = {"recorded": True, "fingerprint": project_fingerprint()}
    reset_from(state, "preview")
    save(state)
    print("Recorded the current build fingerprint.")
    return 0


def evidence_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_file() or not path.read_bytes().strip():
        sys.exit(f"error: evidence is missing or empty: {path}")
    return path


def cmd_record_preview(args: argparse.Namespace) -> int:
    state = load()
    ensure_stage(state, "preview")
    if not state["build"]["recorded"] or not project_current(state, "build.fingerprint"):
        sys.exit("error: build fingerprint is missing or stale")
    path = evidence_path(args.evidence)
    state["preview"] = {
        "passed": True,
        "approved": False,
        "evidence": str(path),
        "evidence_fingerprint": file_fingerprint(path),
        "fingerprint": project_fingerprint(),
    }
    reset_from(state, "user-review")
    save(state)
    print(f"Recorded working preview evidence from {path}.")
    return 0


def cmd_approve_preview(_: argparse.Namespace) -> int:
    state = load()
    ensure_stage(state, "user-review")
    if not state["preview"]["passed"] or not project_current(state, "preview.fingerprint"):
        sys.exit("error: preview evidence is missing or stale")
    state["preview"]["approved"] = True
    reset_from(state, "validate")
    save(state)
    print("Approved the current working preview fingerprint.")
    return 0


def cmd_record_validation(args: argparse.Namespace) -> int:
    state = load()
    ensure_stage(state, "validate")
    if not state["preview"]["approved"] or not project_current(state, "preview.fingerprint"):
        sys.exit("error: citizen preview approval is missing or stale")
    path = evidence_path(args.evidence)
    if "ALL CHECKS PASSED" not in path.read_text():
        sys.exit("error: validation evidence does not contain ALL CHECKS PASSED")
    state["validation"] = {
        "passed": True,
        "last_run": now_utc(),
        "evidence": str(path),
        "evidence_fingerprint": file_fingerprint(path),
        "fingerprint": project_fingerprint(),
    }
    reset_from(state, "containerize")
    save(state)
    print(f"Recorded passing validation evidence from {path}.")
    return 0


def cmd_record_image(args: argparse.Namespace) -> int:
    state = load()
    ensure_stage(state, "containerize")
    if not state["validation"]["passed"] or not project_current(state, "validation.fingerprint"):
        sys.exit("error: validation evidence is missing or stale")
    if not args.image_id.startswith("sha256:"):
        sys.exit("error: image ID must be the sha256 ID returned by docker image inspect")
    state["container"].update(
        {
            "image_built": True,
            "tag": args.tag,
            "image_id": args.image_id,
            "fingerprint": container_fingerprint(),
        }
    )
    state["pr_url"] = None
    save(state)
    print(f"Recorded local image {args.tag} ({args.image_id}).")
    return 0


def cmd_record_pr(args: argparse.Namespace) -> int:
    state = load()
    ensure_stage(state, "ship")
    if state["repo_provider"] == "local":
        sys.exit(
            "error: local drafts need a corporate repository adapter before a PR can be recorded"
        )
    prior_failure = prior_delivery_evidence_current(state)
    if prior_failure:
        sys.exit(f"error: {prior_failure}")
    if not valid_url(args.url):
        sys.exit("error: pull-request URL must be a non-empty HTTPS page URL")
    state["pr_url"] = args.url
    save(state)
    print(f"Recorded pull request {args.url}.")
    return 0


def cmd_advance(_: argparse.Namespace) -> int:
    state = load()
    current = state["stage"]
    if current == "done":
        print("Already done: the PR is ready for the internal delivery pipeline.")
        return 0
    failure = gate_failure(state, current)
    if failure:
        print(f"BLOCKED: cannot leave {current!r} — {failure}", file=sys.stderr)
        return 2
    next_stage = STAGES[STAGES.index(current) + 1]
    state["stage"] = next_stage
    save(state)
    print(f"Advanced: {current} -> {next_stage}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_parser = sub.add_parser("init", help="create state.json")
    init_parser.add_argument("--name", required=True, help="application slug")
    init_parser.set_defaults(func=cmd_init)

    sub.add_parser("stage", help="print the current stage").set_defaults(func=cmd_stage)
    show_parser = sub.add_parser("show", help="show friendly progress")
    show_parser.add_argument("--json", action="store_true", help="print complete JSON state")
    show_parser.set_defaults(func=cmd_show)

    get_parser = sub.add_parser("get", help="print one dotted field")
    get_parser.add_argument("key")
    get_parser.set_defaults(func=cmd_get)

    set_parser = sub.add_parser("set", help="set one approved input field")
    set_parser.add_argument("key")
    set_parser.add_argument("value")
    set_parser.set_defaults(func=cmd_set)

    rewind_parser = sub.add_parser("rewind", help="move backward and clear later evidence")
    rewind_parser.add_argument("stage", choices=STAGES[:-1])
    rewind_parser.set_defaults(func=cmd_rewind)

    sub.add_parser("approve-plan", help="approve and fingerprint PLAN.md").set_defaults(
        func=cmd_approve_plan
    )
    sub.add_parser("record-build", help="verify and fingerprint the build").set_defaults(
        func=cmd_record_build
    )

    preview_parser = sub.add_parser("record-preview", help="record executable preview evidence")
    preview_parser.add_argument("--evidence", required=True)
    preview_parser.set_defaults(func=cmd_record_preview)

    sub.add_parser("approve-preview", help="approve the working preview").set_defaults(
        func=cmd_approve_preview
    )

    validation_parser = sub.add_parser(
        "record-validation", help="record passing validation evidence"
    )
    validation_parser.add_argument("--evidence", required=True)
    validation_parser.set_defaults(func=cmd_record_validation)

    image_parser = sub.add_parser("record-image", help="record a locally inspected image")
    image_parser.add_argument("--tag", required=True)
    image_parser.add_argument("--image-id", required=True)
    image_parser.set_defaults(func=cmd_record_image)

    pr_parser = sub.add_parser("record-pr", help="record a real pull-request URL")
    pr_parser.add_argument("--url", required=True)
    pr_parser.set_defaults(func=cmd_record_pr)

    sub.add_parser("advance", help="advance if the current evidence gate passes").set_defaults(
        func=cmd_advance
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
