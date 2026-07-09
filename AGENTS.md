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

## Data access

Data is **preconfigured** in `src/app/data/` — no connection setup. Apps read
data ONLY through this interface, so mock and real sources are interchangeable:

```python
from app.data import get_source, list_sources

for s in list_sources():          # catalog for a picker/menu
    print(s.key, s.label, s.description)

rows = get_source("stocks").fetch()   # list[dict] rows; keys == source.fields
```

Preconfigured sources today: **`stocks`** and **`bonds`** (static mock data in
`stocks.py` / `bonds.py`). Each implements the `DataSource` protocol in
`base.py`: `key`, `label`, `description`, `fields`, `fetch() -> list[Row]`.

**To go from mock to real data:** replace one source's `fetch()` body with a
real query/HTTP call and keep `key`, `label`, `fields`, and the return shape
(a list of flat dict rows) the same. No app code changes. Add a new source by
dropping a class next to `stocks.py` and registering it in `data/__init__.py`.

## The workflow

This repo is driven by the `/citizen-app` skill in `.claude/skills/citizen-app/`.
It is a staged state machine backed by `.plan/state.json`. Do not skip stages
or edit state by hand — run the skill.
