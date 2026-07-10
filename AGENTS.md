# citizen-template

Template and repo-local skill that guide a non-programmer from an idea to a
locally previewed, tested, container-ready pull request. Python 3.11,
uv-managed, import package `app` under `src/app/`.

## Commands

```bash
uv run pytest tests/test_state.py -q                 # focused state-machine tests
uv run pytest                                        # full unit and contract suite
uv run ruff check .                                  # lint; add --fix for safe fixes
uv run ruff format --check .                         # formatting check
uv run basedpyright                                  # types for app, tests, and skill scripts
uv run pre-commit run --all-files                    # complete local pre-PR gate
uv run .agents/skills/citizen-app/scripts/state.py --help
uv run /Users/jacob/Development/jacob-agent-skills/skills/jacob-create-skill/scripts/validate_skill.py .agents/skills/citizen-app
```

The final command uses a maintainer-local skill path; update it if that skill is
installed elsewhere, and do not document a replacement until it has been run.

## Structure

- `.agents/skills/citizen-app/SKILL.md` — workflow dispatcher and citizen-facing rules.
- `.agents/skills/citizen-app/stages/` — one playbook per persisted state-machine stage.
- `.agents/skills/citizen-app/scripts/state.py` — only authority allowed to change workflow stage.
- `.agents/skills/citizen-app/scripts/preflight.py` — early local-tool and authentication checks.
- `.agents/skills/citizen-app/scripts/preview.py` — executable dashboard/job preview evidence.
- `.agents/skills/citizen-app/scripts/validate.py` — lint, type, test, render, and smoke gate.
- `.agents/skills/citizen-app/assets/` — source and container starters copied by the build stages.
- `src/app/data/` — preconfigured stocks/bonds sources and the stable mock-to-real seam.
- The generated plan artifact contains approved requirements and is committed with apps.
- The generated state artifact is local, git-ignored, and changed only by the workflow CLI.
- `CORPORATE_INTEGRATION.md` — source of truth for network-only delivery integration.

## Conventions

- The package import remains `app`; only `[project].name` changes to the generated repository slug.
- Add dependencies with `uv add` or `uv add --dev`; never use `pip` or hand-edit lock data.
- Keep input/output boundaries in the UI or job entry point and put testable decisions in the generated core module under `src/app/`.
- Access bundled sample data through `app.data.get_source`/`list_sources`; replace a source's `fetch()` implementation without changing its key, fields, or row shape.
- Read numeric row values with `app.data.as_float` because row values are intentionally typed as `object`.
- Read runtime configuration from `os.environ`; `.env` files are local only and corporate secrets are injected by the platform.
- Treat `.agents/skills/citizen-app/scripts/state.py` as a deterministic CLI: judgment stays in stage prose, gates and evidence checks stay in code.
- Keep citizen-facing language free of git, container, cron, and framework jargon unless immediately translated.

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
dropping a class next to `stocks.py` and registering it in `src/app/data/__init__.py`.

**Presenting a source (reusable view helpers):**
- Jobs: `from app.data.summary import summarize` — a plain-text count + per-field
  min/max/avg. Stdlib only.
- UI: `from app.present import show_source` — one call renders metrics + table +
  bar chart. Ships in UI apps only (needs streamlit + pandas, added at build).

## Gotchas

- A pull request is intentionally the finish line because deployment occurs inside an unavailable corporate network; never call the PR live or deployed.
- Container files use a public uv base image only as a local placeholder; the internal mirror is unresolved in `CORPORATE_INTEGRATION.md`.
- GitHub.com publishing is a development adapter, not evidence that GitHub Enterprise or Azure DevOps integration is complete.
- Changing the approved plan or application files makes later evidence stale; rewind with `state.py rewind <stage>` and repeat the gates.
- Generated applications may have no `.env`; run commands must work without `--env-file` unless a real local environment file exists.

## Git and pull requests

- Preserve unrelated working-tree changes and inspect them before editing overlapping files.
- Use a branch beginning with codex/ by default until the corporate branch policy replaces it.
- Include the approved plan, preview status, validation result, and container result in the PR description.
- Do not add public CI workflows; Jenkins and required status checks are corporate integration work.

## Boundaries

- **Always:** run the focused tests for changed workflow code, then the complete pre-commit and pytest gates.
- **Always:** keep `.agents/skills/citizen-app/` as the single workflow source of truth.
- **Ask first:** making a repository public, weakening a quality gate, or changing the citizen-visible definition of done.
- **Ask first:** introducing a provider-specific deployment assumption not recorded in the corporate integration checklist.
- **Never:** invent internal URLs, credentials, registry names, Jenkins libraries, namespaces, or approval rules.
- **Never:** edit the generated workflow state JSON by hand or allow generic setters to mutate `stage`.
- **Never:** commit secrets or claim that an unverified PR has deployed an application.

<!-- Maintenance: add a rule only after an observed failure (one sentence).
Update commands in the same PR that changes them. Prune regularly: if
removing a line would not cause agent mistakes, remove it. -->
