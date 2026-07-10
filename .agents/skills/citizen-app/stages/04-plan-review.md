# Stage 04 — approve the plan

Goal: obtain explicit approval of the current written plan before writing
application code.

Show `.plan/PLAN.md` in full, then summarize in three short sentences: what the
person gets, what information it uses, and what will prove it works. Ask:

> Does this describe the first version you want me to build, or should we change anything?

If they request a change, rewind to the interview, update both the plan and
machine-readable requirements, and show the complete revised plan again:

```bash
uv run .agents/skills/citizen-app/scripts/state.py rewind interview
```

Only after a clear yes, fingerprint and approve the exact plan they saw:

```bash
uv run .agents/skills/citizen-app/scripts/state.py approve-plan
uv run .agents/skills/citizen-app/scripts/state.py advance
```

The script rejects approval if the plan is missing, empty, or lacks recorded
success criteria. Editing the plan later makes the approval stale.
