# AGENTS.md

## Project

A citizen-developer application scaffolded from the citizen-app template.
uv-managed, Python 3.11, single `pyproject.toml`. Import package: `app`
(under `src/app/`) — the package name is stable; only the `[project].name`
tracks the repo slug.

## Conventions

- Python 3.11 only. Never `pip install`; every dep lands in `pyproject.toml`
  via `uv add`.
- Lint/format: ruff. Types: basedpyright (basic mode). Both run in pre-commit.
- `.env` is a symlink to the active `.env.<environment>`; code reads
  `os.environ` only. Run with `uv run --env-file .env ...`.
- Tests in `tests/`, run with `uv run pytest`.

## The workflow

This repo is driven by the `/citizen-app` skill in `.claude/skills/citizen-app/`.
It is a staged state machine backed by `.plan/state.json`. Do not skip stages
or edit state by hand — run the skill.
