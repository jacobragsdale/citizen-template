# Stage 03 — interview

Goal: understand the app well enough to build it, and write a plan the citizen
can approve. Interview conversationally — a few questions at a time, plain
language, follow up on vague answers. Do not dump a form.

## Cover every topic (copy this checklist and tick as you go)

Shared:
- [ ] **Goal** — one sentence: what does this app do, for whom?
- [ ] **Inputs** — what does it need to work? (typed values, a file, an API key,
      a database, a spreadsheet?)
- [ ] **Data source** — the app comes with ready-made data built in. List what's
      available and let them pick one or more (see "Present the data catalog"
      below). Record their choice(s).
- [ ] **Outputs** — what does it produce or show? (a number, a chart, a file, an
      email, a message somewhere?)
- [ ] **Secrets/config** — any passwords, API keys, or URLs? (These become
      environment variables — never hardcode them.)
- [ ] **Done looks like** — 2–4 concrete things that must be true for it to be a
      success. These become the acceptance criteria.
- [ ] **Out of scope** — one or two things it explicitly will NOT do (guards
      against scope creep).

If `app_type == "ui"`:
- [ ] **Screens/controls** — what does the person see and click? What do they
      type in, and what appears when they do?

If `app_type == "job"`:
- [ ] **Schedule** — how often should it run? Translate their words into a cron
      expression (e.g. "every morning at 7" → `0 7 * * *`) and read it back.
- [ ] **Run target** — where does the output go when it runs unattended?

## Present the data catalog

The template ships preconfigured data sources — no setup needed. Don't guess
what's available; list it live:

```bash
uv run python -c "from app.data import list_sources; [print(f'- {s.label} ({s.key}): {s.description}') for s in list_sources()]"
```

Read the list to the citizen in plain language ("Your app can use this ready-made
data: …") and ask which one(s) they want. Today that's **Stocks** and **Bonds**.
Capture the chosen keys for `requirements.data_sources` (e.g. `["stocks"]`).

## Write the plan

When every box is ticked, write `.plan/PLAN.md` using this exact structure:

```markdown
# PLAN — citizen-<slug>

## What we're building
<one paragraph in plain language>

## Type
<UI (Streamlit) | Scheduled job (CronJob, schedule: `<cron>`)>

## Inputs
- ...

## Data source(s)
- <Stocks | Bonds> — why this app uses it

## Outputs
- ...

## Configuration / secrets (environment variables)
- `NAME` — what it's for

## Acceptance criteria (done looks like)
- [ ] ...

## Out of scope
- ...
```

Record the essentials in state (so later stages don't re-ask):

```bash
uv run .claude/skills/citizen-app/scripts/state.py set requirements '{"goal": "...", "data_sources": ["stocks"], "schedule": "0 7 * * *", "env": ["NAME"]}'
uv run .claude/skills/citizen-app/scripts/state.py advance
```

## Exit gate

None here — the approval gate is the next stage. Advance once `.plan/PLAN.md`
exists and every checklist box is ticked.
