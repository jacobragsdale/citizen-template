# Stage 02 — choose type

Goal: find out whether they want something with a screen, or something that runs
on a schedule. This decides every template used downstream.

## Do this

Ask the citizen to pick, in plain language (use the AskUserQuestion tool):

- **A UI** — "a web page with buttons, boxes to type in, and things to look at,
  that you open in a browser." (Built with Streamlit.) → `app_type = "ui"`
- **A scheduled job** — "code that runs by itself on a timer — like a report
  that lands in your inbox every morning — with no screen." (A Kubernetes
  CronJob.) → `app_type = "job"`

If they are unsure, ask one clarifying question: "Do you need to look at it and
click things (UI), or should it just happen automatically on a schedule (job)?"

## State written

```bash
uv run .claude/skills/citizen-app/scripts/state.py set app_type ui   # or: job
uv run .claude/skills/citizen-app/scripts/state.py advance
```

## Exit gate

None. Only advance once `app_type` is set to `ui` or `job`.
