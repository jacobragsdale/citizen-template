#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Own the /citizen-app workflow state machine.

State lives in .plan/state.json. This script is the ONLY thing that changes
`stage`: the agent never advances by hand, so stages cannot run out of order
and gates cannot be skipped. Run it; do not reimplement it.

Subcommands:
  init --name SLUG   create .plan/state.json (no-op if it already exists)
  stage              print just the current stage (for dispatch)
  show               print the full state + a human summary
  get KEY            print one field (dotted, e.g. validation.passed)
  set KEY VALUE      set one field (VALUE parsed as JSON, else kept as string)
  advance            move to the next stage, enforcing that stage's exit gate

Exit codes: 0 ok; 2 gate not satisfied; 1 usage/other error.
"""

import argparse
import json
import sys
from pathlib import Path

STATE_PATH = Path(".plan/state.json")

# The rails. Order is fixed; each stage may declare an exit gate that must hold
# before `advance` will leave it. Gate = (dotted field, required value, message).
STAGES = [
    "scaffold",
    "choose-type",
    "interview",
    "plan-review",
    "build",
    "validate",
    "preview",
    "containerize",
    "ship",
    "done",
]

GATES: dict[str, tuple[str, object, str]] = {
    "plan-review": ("plan_approved", True, "the user has not approved PLAN.md yet"),
    "validate": ("validation.passed", True, "validation has not passed yet"),
    "preview": ("previewed", True, "the user has not viewed the app yet"),
    "containerize": ("image_built", True, "the container image has not built locally yet"),
    "ship": ("pr_url", "__set__", "no pull request URL recorded — the app is not published yet"),
}

INITIAL = {
    "stage": "scaffold",
    "app_name": None,  # citizen-<slug>
    "app_type": None,  # "ui" | "job"
    "repo_url": None,
    "requirements": {},
    "plan_approved": False,
    "validation": {"passed": False, "last_run": None},
    "previewed": False,
    "image_built": False,
    "pr_url": None,
}


def load() -> dict:
    if not STATE_PATH.exists():
        sys.exit("error: no .plan/state.json — run `state.py init --name <slug>` first")
    return json.loads(STATE_PATH.read_text())


def save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")


def dotted_get(state: dict, key: str) -> object:
    node = state
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            sys.exit(f"error: no such field {key!r}")
        node = node[part]
    return node


def dotted_set(state: dict, key: str, value: object) -> None:
    parts = key.split(".")
    node = state
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def cmd_init(args: argparse.Namespace) -> int:
    if STATE_PATH.exists():
        print(f"{STATE_PATH} already exists — resuming at stage '{load()['stage']}'")
        return 0
    state = dict(INITIAL)
    state["app_name"] = args.name
    save(state)
    print(f"initialized {STATE_PATH} at stage 'scaffold' for {args.name!r}")
    return 0


def cmd_stage(_: argparse.Namespace) -> int:
    print(load()["stage"])
    return 0


def cmd_show(_: argparse.Namespace) -> int:
    state = load()
    print(json.dumps(state, indent=2))
    i = STAGES.index(state["stage"])
    print(f"\nStage {i + 1}/{len(STAGES)}: {state['stage']}", file=sys.stderr)
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    val = dotted_get(load(), args.key)
    print(val if not isinstance(val, (dict, list)) else json.dumps(val))
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    state = load()
    try:
        value: object = json.loads(args.value)
    except json.JSONDecodeError:
        value = args.value
    dotted_set(state, args.key, value)
    save(state)
    print(f"set {args.key} = {value!r}")
    return 0


def cmd_advance(_: argparse.Namespace) -> int:
    state = load()
    current = state["stage"]
    if current == "done":
        print("already at 'done'")
        return 0
    gate = GATES.get(current)
    if gate:
        field, required, message = gate
        actual = dotted_get(state, field)
        satisfied = actual is not None if required == "__set__" else actual == required
        if not satisfied:
            print(f"BLOCKED: cannot leave '{current}' — {message}", file=sys.stderr)
            return 2
    nxt = STAGES[STAGES.index(current) + 1]
    state["stage"] = nxt
    save(state)
    print(f"advanced: {current} -> {nxt}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="create state.json")
    p_init.add_argument("--name", required=True, help="app name (citizen-<slug>)")
    p_init.set_defaults(func=cmd_init)
    sub.add_parser("stage", help="print current stage").set_defaults(func=cmd_stage)
    sub.add_parser("show", help="print full state").set_defaults(func=cmd_show)
    p_get = sub.add_parser("get", help="print one field")
    p_get.add_argument("key")
    p_get.set_defaults(func=cmd_get)
    p_set = sub.add_parser("set", help="set one field")
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_set.set_defaults(func=cmd_set)
    p_adv = sub.add_parser("advance", help="advance to next stage (enforces gate)")
    p_adv.set_defaults(func=cmd_advance)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
