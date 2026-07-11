# Stage 05 — build

Goal: implement the approved plan with a small functional core, a thin UI or
job entry point, and behavior tests tied to the success criteria.

## Project identity

Set `[project].name` to the repository slug while keeping the import package
named `app`:

```text
uv run .agents/skills/citizen-app/scripts/project.py set-identity --name citizen-<slug>
```

## Copy the correct starters

Use `ui` or `job` to match the recorded choice. The helper copies the correct
starter idempotently and adds dashboard dependencies when needed:

```text
uv run .agents/skills/citizen-app/scripts/project.py apply-starter --type ui
```

## Implement the plan

- Put calculations, validation, transformations, and decisions in `core.py`.
- Keep Streamlit controls/rendering or job I/O/delivery in the entry point.
- Wire `requirements.data_sources` through `app.data.get_source`; keep the
  source picker only when the citizen asked to switch between several sources.
- Use `app.present.show_source` for the reusable dashboard metrics/table/chart
  view, then extend it only where the approved plan requires something different.
- Use `app.data.as_float(row, field)` for numeric row arithmetic. Row values are
  typed as `object`, so direct `float(row[field])` fails the type gate.
- Read configuration from `os.environ` and document names in `.env.example`;
  never hardcode or request real secrets.
- Use run commands without `--env-file` when no `.env` exists. If local secrets
  are needed, create an ignored `.env.dev` and `.env` symlink yourself.
- For Streamlit tables and charts use `width="stretch"`, not the removed
  `use_container_width` option.
- For pandas, keep metric logic in `core.py`; prefer NumPy scalar reductions,
  cast boolean-index/groupby results when stubs lose the DataFrame type, and
  convert Series-wide truth checks to `bool(...)` in tests.
- For several job sources, use an explicit key list and loop; do not silently
  process only the first chosen source.
- Implement clear loading, empty, invalid-input, and external-failure states.
- Preserve a real automated-job dry run: it must execute configuration and
  transformation wiring while suppressing irreversible delivery only.

## Tests and handoff docs

Write behavior-named pytest tests for every acceptance criterion that can be
checked locally. Expected values come from the approved plan, not copied from
the implementation. Use pure functions and small representative inputs; do not
mock framework internals.

Write `.plan/acceptance.json` with schema version 1 and one entry per criterion:

```json
{
  "schema_version": 1,
  "criteria": [
    {
      "criterion": "A user can compare several stock symbols",
      "tests": ["tests/test_stock_dashboard.py::test_multiple_symbols_are_compared"],
      "preview_assertions": ["comparison_symbol_count"]
    }
  ]
}
```

For dashboard interactions that generic rendering cannot prove, add
`tests/preview_assertions.py`. It must execute the representative AppTest
interactions and fail on an unmet result; the preview helper records its output.

Replace the generated app README sections with:

- what it does and who it is for;
- preview/run commands that work in a fresh clone;
- required configuration names without values;
- job schedule/timezone/manual-run details when applicable; and
- “Delivery status: ready for internal pipeline after PR approval.”

Run the build helper only after the entry point, core, and real behavior tests
exist and instructional placeholders are gone. It records current lint,
formatting, type, compile, and application-specific test evidence; failing or
stale evidence cannot advance:

```bash
uv run .agents/skills/citizen-app/scripts/build.py
uv run .agents/skills/citizen-app/scripts/state.py advance
```
