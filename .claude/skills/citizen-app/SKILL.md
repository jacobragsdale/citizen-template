---
name: citizen-app
description: "Guide a non-programmer from idea to a published GitHub app. Use when the user runs /citizen-app or asks to build/create/ship an app, tool, dashboard, or scheduled job and does not want to deal with git, Docker, packaging, or pull requests."
metadata:
  author: jacob
disable-model-invocation: true
---

# Citizen App — idea to published app, on rails

Walk a non-technical person from an idea to a working application published on
GitHub as a pull request. They should never need to know about git, packages,
Docker, or PRs. You do all of that; you talk them through the rest in plain
language.

**Read `LEARNINGS.md` in this folder before starting.**

## The one rule that keeps this on rails

`scripts/state.py` owns `.plan/state.json`, and it is the ONLY thing that
decides what happens next. You never guess the next step, never skip a stage,
never edit state by hand, and never advance past a gate that the script blocks.
Each turn: read the stage, do exactly that stage's playbook, then try to
advance. If `advance` prints `BLOCKED`, stay in the stage and resolve the gate.

## How to talk to the citizen

- Plain language. No jargon — no "commit", "branch", "container", "dependency"
  unless you immediately explain it in one friendly clause.
- One idea per turn. Ask few questions at a time and wait.
- Never show raw errors or stack traces. Translate failures into "here's what
  went wrong and what I'm doing about it."
- Never ask them to run a command. You run everything.

## Start / resume

On every invocation, first show where things stand:

```bash
uv run .claude/skills/citizen-app/scripts/state.py show
```

If that prints `no .plan/state.json`, this is a brand-new run: go straight to
the scaffold playbook, which creates the state file itself (it needs a name
first). Otherwise you are resuming — invoking `/citizen-app` again always picks
up at the saved stage.

## The dispatch loop

1. Get the current stage: `state.py stage`.
2. Read the matching playbook in `stages/` and follow it exactly:

   | stage | playbook | what it does |
   |---|---|---|
   | `scaffold` | `stages/01-scaffold.md` | name it `citizen-<slug>`, create the GitHub repo from this template |
   | `choose-type` | `stages/02-choose-type.md` | ask: a UI, or a scheduled job? |
   | `interview` | `stages/03-interview.md` | interview thoroughly, write `.plan/PLAN.md` |
   | `plan-review` | `stages/04-plan-review.md` | show the plan; **gate:** they must approve |
   | `build` | `stages/05-build.md` | build the app from the matching template |
   | `validate` | `stages/06-validate.md` | run checks + a smoke run; **gate:** must pass |
   | `containerize` | `stages/07-containerize.md` | write the Dockerfile; **gate:** image builds |
   | `ship` | `stages/08-ship.md` | publish to GitHub; **gate:** a PR URL exists |
   | `done` | — | tell them the app is live and hand them the PR link |

3. When the playbook's work is complete, run `state.py advance`. If it prints
   `BLOCKED`, the gate is not met — stay here and finish the gate's work.
4. Repeat until stage is `done`.

Each playbook is self-contained and says which fields to write to state (via
`state.py set`) and what its exit gate needs. Do not read ahead — run one stage
at a time.

## Bundled resources

- `scripts/state.py` — **run** it; it owns stage transitions and gates.
- `stages/*.md` — **read** the one matching the current stage, then execute it.
- `assets/` — templates the build and containerize stages copy from.

## Improving this skill

Before executing, read `LEARNINGS.md` in this skill's folder — entries there
override the instructions above. After use, if the user corrected you or the
outcome surprised you, append one dated line to `LEARNINGS.md`:
`- YYYY-MM-DD: <what happened> → <what to do instead>`. Do not edit SKILL.md
directly; lessons are folded in deliberately, not on the fly.
