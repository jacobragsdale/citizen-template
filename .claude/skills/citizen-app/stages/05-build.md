# Stage 05 — build

Goal: turn the approved plan into working code, starting from the matching
template so you are never staring at a blank file.

## Steps

1. Set the project name to match the repo (does not touch imports; package stays
   `app`):
   ```bash
   uv run - <<'PY'
   import pathlib, re
   slug = pathlib.Path.cwd().name  # citizen-<slug>
   p = pathlib.Path("pyproject.toml"); t = p.read_text()
   p.write_text(re.sub(r'(?m)^name = ".*"$', f'name = "{slug}"', t, count=1))
   PY
   ```

2. Copy the starter for this app type into the package:

   **UI:**
   ```bash
   cp .claude/skills/citizen-app/assets/ui-streamlit/ui.py.template src/app/ui.py
   cp .claude/skills/citizen-app/assets/ui-streamlit/present.py.template src/app/present.py
   uv add streamlit pandas
   ```
   Run command is `uv run --env-file .env streamlit run src/app/ui.py`.
   `app.present.show_source(source)` renders metrics + table + chart in one call.

   **Job:**
   ```bash
   cp .claude/skills/citizen-app/assets/job-cronjob/job.py.template src/app/job.py
   ```
   Run command is `uv run --env-file .env python -m app.job`.

   Then create the local env file the run/preview commands load (both `--env-file
   .env`). It stays out of git, and starting from `.env.example` means the command
   works even for a no-secrets app:
   ```bash
   cp .env.example .env
   ```

3. Wire in the data source(s) from `requirements.data_sources` — the data is
   preconfigured, so just point at it (never invent a connection or hardcode
   rows):
   - **UI:** if the plan uses one source, set it directly
     (`source = get_source("stocks")`) and drop the `st.selectbox`; keep the
     picker only if the citizen wanted to switch between several.
   - **Job:** set `SOURCE_KEY = "stocks"` (or `"bonds"`) to their choice. If the
     plan uses several sources, use `SOURCE_KEYS = ["stocks", "bonds"]` and loop.
   - Access rows only via `from app.data import get_source` / `list_sources`.
   - **Rows are typed `object`.** Any arithmetic on a field (`float(row["price"])`,
     comparisons, `abs(...)`) will fail the basedpyright gate. Read numbers with
     the helper: `from app.data import as_float` → `as_float(row, "price")`. For
     pandas aggregations that mis-infer (e.g. `groupby(...).mean()`), narrow with
     `float(series.to_numpy(dtype=float).mean())` rather than a bare `float(...)`.

4. Implement the plan by editing the copied file:
   - Replace the `APP_TITLE` / `APP_DESCRIPTION` placeholders (UI) with real text.
   - Replace the starter body with the real inputs, work, and outputs from
     `.plan/PLAN.md`, operating on the rows from the data source.
   - Read every secret/config value from `os.environ` and add each one to
     `.env.example` with a comment. Never hardcode secrets.
   - Add any new dependency with `uv add <pkg>` — never edit pyproject deps by
     hand, never `pip install`.

5. Write at least one real `pytest` test in `tests/` that checks a piece of the
   plan's logic (not just that it imports). Keep testable logic in plain
   functions so it can be tested without a running server.

6. Update the README "Running" table with the run command above, and (for jobs)
   note the schedule from the plan.

## State written

None required. Advance when the code reflects the plan:
```bash
uv run .claude/skills/citizen-app/scripts/state.py advance
```

## Exit gate

None — the real check is the next stage (validate), which will bounce you back
here if anything is broken.
