# Stage 01 — scaffold

Goal: create or adopt a safe working repository and discover missing tools
before the citizen invests time in the interview.

## First conversation

Ask what they would like to call the app and what they hope it will help with.
Create a lowercase hyphenated name prefixed with `citizen-`, show it, and wait
for confirmation.

Then ask where the draft should live:

- **Private GitHub repository** — the currently implemented publishing path.
- **Only on this computer for now** — safe for trying the workflow, but the
  ship stage will wait for an internal repository integration.

Never create a public repository unless the citizen explicitly requests and
confirms it after you explain that its code and plan will be internet-visible.

## Preflight

Run this before creating anything, with `local` or `github` to match the answer:

```bash
uv run .agents/skills/citizen-app/scripts/preflight.py --provider github --require-container
```

For a standard-user Windows rehearsal whose image will be built by the
fingerprinted external verifier:

```powershell
uv run .agents/skills/citizen-app/scripts/preflight.py --provider local --container-mode external
```

Translate any failure. Core tools and, for GitHub, authentication are immediate
blockers. Docker is checked now when the image will be built locally; external
verification records the same runtime evidence without requiring Docker in the
guest.

## Detect template versus application

```text
uv run .agents/skills/citizen-app/scripts/project.py inspect
```

If `.plan/state.json` exists or the repository name already begins with
`citizen-`, use the Adopt path. Otherwise use Create.

## Create

### Private GitHub repository

Do not assume the template and destination have the same owner. The helper
discovers both, creates a private repository, polls template population, clones
it, and rejects an empty working copy:

```text
uv run .agents/skills/citizen-app/scripts/project.py create-github --name citizen-<slug> --destination ../citizen-<slug>
```

### Local draft

```text
uv run .agents/skills/citizen-app/scripts/project.py create-local --name citizen-<slug> --destination ../citizen-<slug>
```

Run every remaining command from the new sibling folder.

## Adopt and record

From the application repository:

```text
uv run .agents/skills/citizen-app/scripts/state.py init --name citizen-<slug>
uv run .agents/skills/citizen-app/scripts/state.py record-workspace --provider github --visibility private
uv run .agents/skills/citizen-app/scripts/state.py advance
```

For a local draft, use `record-workspace --provider local`.

Enterprise GitHub and Azure DevOps creation remain blocked until the provider
contract in `CORPORATE_INTEGRATION.md` is completed. Do not guess internal
commands or silently substitute a public repository.

Preflight writes capability evidence with `--output .plan/preflight.json`.
Missing browser capability is informational here: dashboard building can
continue, but the citizen-visible approval gate will wait until a browser is
available. A local-only repository is also a supported finish line.
