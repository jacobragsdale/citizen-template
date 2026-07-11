# Stage 06 — produce a working preview

Goal: execute the current application with representative data and give the
citizen concrete output to review before the engineering quality gate.

Run the deterministic preview helper:

```bash
uv run .agents/skills/citizen-app/scripts/preview.py
```

It reads the application type from state, executes the Streamlit page through
`AppTest` or runs the job in dry-run mode, and writes a short human summary plus
versioned `.plan/preview/summary.json`. Dashboard evidence inventories controls,
metrics, tables, charts, warnings, errors, and acceptance-specific interactions.

For a dashboard, also start the local Streamlit server on an available port.
Open that exact local URL using the available browser capability and show the
citizen the actual page or a current screenshot. Exercise the important
controls with representative data. If the default port is occupied, choose a
free one and keep the command and link consistent. Do not substitute a
server-health response for page execution.

For an automated job, show the dry-run output in full and explain where the real
result will go, when it will run, and what irreversible delivery was suppressed.

If preview execution fails, translate the failure, rewind to build, fix it, and
repeat:

```bash
uv run .agents/skills/citizen-app/scripts/state.py rewind build
```

Once the preview works, record the evidence file printed by the helper and
advance:

```bash
uv run .agents/skills/citizen-app/scripts/state.py record-preview --evidence .plan/preview/summary.json
uv run .agents/skills/citizen-app/scripts/state.py advance
```

The structured evidence path is the same for dashboards and automated jobs.
