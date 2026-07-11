# Stage 07 — approve the working result

Goal: let the citizen judge the application they can see, not merely its plan.

Ask three concrete questions, one or two at a time:

1. Does this show or produce the right information?
2. Is anything confusing, missing, or harder than expected?
3. Does this working version meet the success statements in the plan?

If they request any change, rewind to build, implement it, and repeat preview
and review. Even a small code change invalidates the old evidence.

```bash
uv run .agents/skills/citizen-app/scripts/state.py rewind build
```

Only after an explicit yes, approve the fingerprint of the exact preview they
saw and advance:

```bash
uv run .agents/skills/citizen-app/scripts/state.py record-browser-review
uv run .agents/skills/citizen-app/scripts/state.py approve-preview
uv run .agents/skills/citizen-app/scripts/state.py advance
```

Run `record-browser-review` only for dashboards, after the actual current page
was available to the reviewer. Automated jobs use their full dry-run output.
If no browser is available, explain that automated rendering passed but visible
approval is still waiting; do not treat that capability gap as a render failure.

Do not interpret silence, uncertainty, or “I guess” as approval; help them name
what feels wrong and iterate.
