# Stage 08 — ship (publish gate)

Goal: publish the finished app to GitHub as a pull request. This is the finish
line — the workflow is not done until a PR exists.

## Do this

1. Put the work on a branch and save it (the citizen never types git):
   ```bash
   git switch -c build/initial-app
   git add -A
   git commit -m "Build <app name> from approved plan"
   git push -u origin build/initial-app
   ```

2. Open the pull request, using the plan as its description:
   ```bash
   gh pr create --title "Build <app name>" --body-file .plan/PLAN.md --base main --head build/initial-app
   ```

3. Capture the PR URL and record it, then advance to finish:
   ```bash
   PR_URL=$(gh pr view --json url --jq .url)
   uv run .claude/skills/citizen-app/scripts/state.py set pr_url "$PR_URL"
   uv run .claude/skills/citizen-app/scripts/state.py advance
   ```

4. Tell the citizen, in plain language, that their app is now published on
   GitHub, and give them the clickable PR link. Explain a pull request in one
   friendly clause ("a page on GitHub showing everything I built, ready for you
   or a teammate to review and approve").

## Exit gate

`pr_url` must be set (a real URL from `gh pr create`). `advance` prints
`BLOCKED` until it is — the app is not considered shipped without a published PR.
