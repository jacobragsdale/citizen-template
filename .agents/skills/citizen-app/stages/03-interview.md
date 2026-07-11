# Stage 03 — interview and plan

Goal: learn enough to build the right small application without presenting the
citizen with a technical questionnaire.

Ask two or three related questions at a time. Explain why an answer matters and
follow vague answers with an example. Cover every shared topic, then the branch
for the recorded application type.

## Shared topics

- Goal and audience: who uses this and what decision or task becomes easier?
- Inputs: where does the information come from, and can they provide a safe
  representative sample?
- Starting data: present the bundled source catalog and ask whether stocks,
  bonds, both, or a future corporate source best represents the first preview.
- Outputs: what must the person see, receive, or find afterward?
- Freshness and scale: how much data, and how current must it be?
- Access and sensitivity: who may see it, and does it contain confidential,
  personal, financial, health, or regulated data?
- Configuration: what connection names, URLs, or secrets will the platform
  need to inject? Never ask them to paste a secret into chat or a file.
- Success: three to six observable statements that prove it works.
- Failure: what should the person experience when input is empty, invalid, or
  temporarily unavailable?
- Scope: what useful-looking feature will this first version deliberately omit?

## Dashboard branch

- What should be visible immediately on opening the page?
- Which filters, inputs, tables, charts, or downloads matter?
- What representative data can be used for the preview?
- What should loading, no-data, and error states say?

## Present the bundled data catalog

Do not guess what the current template contains. List it live:

```bash
uv run python -c "from app.data import list_sources; [print(f'- {s.label} ({s.key}): {s.description}') for s in list_sources()]"
```

Explain that these are safe deterministic preview sources, not live market
feeds. Record chosen keys in `requirements.data_sources`. If the citizen needs a
corporate system, choose the closest representative sample now and capture the
real connection as an internal integration requirement.

## Automated-job branch

- In everyday language, when should it run and in which timezone?
- Where does the result go, and who should be notified on failure?
- Is it safe to retry, and how are duplicate outputs prevented?
- How can an operator run it once manually or in a harmless dry-run mode?

## Write `.plan/PLAN.md`

Use this structure. Keep the main sections non-technical; put implementation
terms in the final appendix.

```markdown
# Plan — citizen-<slug>

## What this will make easier
<one short paragraph>

## Who it is for
- ...

## What they will see or receive
- ...

## Information it uses
- source(s), representative sample, freshness, and scale

## Success looks like
- [ ] observable acceptance criterion

## Safety and access
- sensitivity, audience, secrets, and safe failure behavior

## Day-to-day operation
- dashboard refresh expectations OR job schedule, timezone, retries, alerts,
  duplicate safety, and manual run

## Out of scope for the first version
- ...

## Technical handoff
- Type: dashboard | automated job
- Runtime configuration names: `NAME` — purpose
- Container required: yes
- Internal deployment: pending corporate pipeline integration
```

Record a compact machine-readable copy. Include the goal and the complete
acceptance-criteria list; include schedule, timezone, and environment-variable
names when relevant.

Write the structured requirements to `.plan/requirements.json` as UTF-8, then
record them without shell-sensitive JSON quoting:

```bash
uv run .agents/skills/citizen-app/scripts/state.py set requirements --value-file .plan/requirements.json
uv run .agents/skills/citizen-app/scripts/state.py advance
```
