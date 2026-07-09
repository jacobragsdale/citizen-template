# Stage 06 — validate (quality gate)

Goal: prove the app is clean and actually boots before packaging it.

## Do this

1. Run the checker (it reads `app_type` from state and runs the right smoke run):
   ```bash
   uv run .claude/skills/citizen-app/scripts/validate.py
   ```
2. If it exits non-zero, read the SUMMARY, fix the specific failure back in the
   build stage's files (lint, types, a failing test, or a smoke failure meaning
   the app doesn't boot), and run it again. Repeat until it prints
   `ALL CHECKS PASSED`.
   - Fix causes, not symptoms. Do not weaken lint/type rules or delete tests to
     go green. Auto-fixable lint: `uv run ruff check --fix .` and
     `uv run ruff format .`.
   - Explain failures to the citizen plainly ("the app didn't start because …"),
     not as raw errors.
3. Only once it passes, advance. `validate.py` records the result itself
   (`validation.passed` + `validation.last_run` in state), so you do NOT set the
   flag by hand — just advance:
   ```bash
   uv run .claude/skills/citizen-app/scripts/state.py advance
   ```

## Exit gate

`validation.passed == true`, written by `validate.py` on a green run. If you
change any code after passing, re-run `validate.py` — a failing run flips the
flag back to `false`, so the gate reflects the latest run, not an old one.
