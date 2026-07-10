# Stage 02 — choose the experience

Goal: understand the desired outcome first, then confirm whether the result is
something a person opens or something that runs unattended.

Ask one open question:

> What do you wish were easier, and what would you like to have at the end?

Infer the likely shape and confirm it in plain language:

- `ui` — “a page you open to look at information, choose filters, or enter values.”
- `job` — “work that happens by itself and sends or saves a result without a screen.”

Do not ask the citizen to choose Streamlit, CronJob, or another framework. If
both are genuinely needed, choose the smallest first deliverable and record the
other part as out of scope rather than building two applications accidentally.

Record the confirmed choice:

```bash
uv run .agents/skills/citizen-app/scripts/state.py set app_type ui
uv run .agents/skills/citizen-app/scripts/state.py advance
```

Use `job` for the unattended option.
