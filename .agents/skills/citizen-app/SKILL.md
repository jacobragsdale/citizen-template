---
name: citizen-app
description: "Use when a non-programmer asks to build, create, or ship a dashboard, automated report, scheduled job, internal tool, or simple app and wants the agent to handle planning, code, testing, containers, git, and the pull request."
metadata:
  author: jacob
---

# Citizen App — idea to a corporate-ready pull request

Guide a non-technical person from an idea to an application they have seen and
approved, then publish a tested, container-ready pull request for the corporate
delivery pipeline. The pull request is intentionally the handoff point; do not
call the application live or deployed.

Read `LEARNINGS.md` before starting.

## The rails

`scripts/state.py` is the only authority that changes `.plan/state.json` or the
current stage. Run its commands; never edit state by hand, set `stage`, skip a
stage, or record evidence that was not produced in the current revision.

On every invocation:

1. Run `uv run .agents/skills/citizen-app/scripts/state.py show`.
2. If there is no state file, read `stages/01-scaffold.md`.
3. Otherwise run `state.py stage`, read only the matching stage playbook, and
   complete it.
4. Run `state.py advance`. If it prints `BLOCKED`, resolve that gate before
   doing anything later in the workflow.

## How to work with the citizen

- Start with what they wish were easier; infer the technical shape and confirm it.
- Ask a few questions at a time and explain why each answer matters.
- Never ask them to run a command or interpret a raw error.
- Show progress as a plain sentence, not state JSON or engineering terminology.
- Use representative or clearly labeled sample data for the first preview.
- Treat plan approval and working-preview approval as separate explicit decisions.
- Translate failures into what went wrong, what it affects, and what you are doing next.
- Before package installation, container builds, or another slow step, tell the citizen what is starting and that they can step away.

## Stages

| stage | playbook | exit evidence |
|---|---|---|
| `scaffold` | `stages/01-scaffold.md` | a safe working repository and completed preflight |
| `choose-type` | `stages/02-choose-type.md` | dashboard or automated job confirmed |
| `interview` | `stages/03-interview.md` | complete plain-language plan and success criteria |
| `plan-review` | `stages/04-plan-review.md` | explicit approval of the current plan |
| `build` | `stages/05-build.md` | core/entry-point split and behavior tests recorded |
| `preview` | `stages/06-preview.md` | executable preview evidence from the current code |
| `user-review` | `stages/07-user-review.md` | explicit approval of the working result |
| `validate` | `stages/08-validate.md` | lint, format, types, tests, render, and smoke checks pass |
| `containerize` | `stages/09-containerize.md` | local container image ID recorded when required |
| `local-ready` | `stages/10-local-ready.md` | current local evidence preserved without publication |
| `ship` | `stages/11-ship.md` | a real pull-request URL recorded |
| `done` | — | hand off the PR as ready for internal delivery |

If requirements or code change after approval, use `state.py rewind <stage>`
and repeat every invalidated gate. The script rejects stale fingerprints.

## Definition of done

`done` means all of the following:

- the citizen approved the written plan;
- the citizen saw representative output and approved the working result;
- automated checks and type-specific render/dry-run checks passed;
- the container image built locally unless the recorded plan exempts it; and
- the code is in a pull request ready for internal Jenkins and Kubernetes work.

It does not mean the image was pushed, the app was deployed, or the job was
scheduled. Read `../../../CORPORATE_INTEGRATION.md` before changing that
boundary or implementing an internal provider.

## Bundled resources

- `scripts/state.py` — **run** for state transitions, approvals, evidence, and rewinds.
- `scripts/project.py` — **run** for shell-neutral local creation, identity, and starters.
- `scripts/preflight.py` — **run** before repository creation; it fails early on missing tools.
- `scripts/build.py` — **run** for current lint, type, compile, and application-test evidence.
- `scripts/preview.py` — **run** to execute the page or job and write preview evidence.
- `scripts/validate.py` — **run** for the complete local quality gate.
- `scripts/container.py` — **run** to build and execute the type-specific container smoke check.
- `stages/*.md` — **read** only for the current stage.
- `assets/` — copy starters from here; replace their instructional placeholders during build.

## Improving this skill

Before executing, read `LEARNINGS.md` in this skill's folder — entries there
override the instructions above. After use, if the user corrected you or the
outcome surprised you, append one dated line to `LEARNINGS.md`:
`- YYYY-MM-DD: <what happened> → <what to do instead>`. Do not edit SKILL.md
directly; lessons are folded in deliberately, not on the fly.
