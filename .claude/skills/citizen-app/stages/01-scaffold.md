# Stage 01 — scaffold

Goal: turn the citizen's idea into a real, empty GitHub repository made from
this template, and continue the workflow inside that new repository.

## Detect where you are

```bash
git remote get-url origin 2>/dev/null
```

- If origin ends with **`citizen-template`** (or there is no origin): you are in
  the template. Do the **Create** path below.
- If origin ends with **`citizen-<something>`** (an app repo): you are already in
  the freshly cloned app. Do the **Adopt** path below.

## Create path (running in the template)

1. Ask the citizen, in plain language, what they want to call their app (e.g.
   "weekly sales report"). Turn it into a lowercase, hyphenated slug and prefix
   it: `citizen-weekly-sales-report`. Show them the final name and confirm.
2. Check they are signed in to GitHub:
   ```bash
   gh auth status
   ```
   If this fails, stop and tell them, plainly, that you need them to sign in to
   GitHub before you can publish anything — do not continue.
3. Create the repository from this template and clone it as a sibling folder:
   ```bash
   OWNER=$(gh api user --jq .login)
   gh repo create "$OWNER/citizen-<slug>" --template "$OWNER/citizen-template" --public
   git clone "https://github.com/$OWNER/citizen-<slug>.git" "../citizen-<slug>"
   ```
4. Tell the citizen their project now exists on GitHub. From now on, **run every
   command from the new folder** `../citizen-<slug>` (prefix commands with
   `cd ../citizen-<slug> && …`). Re-read the current stage there and continue —
   you will land in the Adopt path, which advances the workflow.

Do NOT run `state.py` in the template — state lives in the app repo only.

## Adopt path (running in the app repo)

1. Create the workflow state and record the repo:
   ```bash
   uv run .claude/skills/citizen-app/scripts/state.py init --name "$(basename "$(git remote get-url origin)" .git)"
   uv run .claude/skills/citizen-app/scripts/state.py set repo_url "$(git remote get-url origin)"
   ```
2. Advance:
   ```bash
   uv run .claude/skills/citizen-app/scripts/state.py advance
   ```

## State written

- `app_name` (via init), `repo_url`.

## Exit gate

None — but do not advance until the app repo exists and you are running inside
it (origin points at `citizen-<slug>`).
