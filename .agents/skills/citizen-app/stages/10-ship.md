# Stage 10 — publish the corporate-ready pull request

Goal: put the approved, validated, container-ready revision in a pull request
for the internal delivery pipeline. This is the intentional local finish line.

Read `repo_provider` from state. The currently implemented provider is GitHub
through `gh`. A local draft, Azure DevOps, or unverified enterprise provider
must stop here and follow `CORPORATE_INTEGRATION.md`; never publish to a
personal public repository as a fallback.

## GitHub provider

Create or resume the branch, commit only the intended app changes, and push:

```bash
git switch codex/build-initial-app 2>/dev/null || git switch -c codex/build-initial-app
git add -A
git commit -m "Build <app name> from approved plan"
git push -u origin codex/build-initial-app
```

Write `.plan/PR_BODY.md` from the approved plan plus this verified handoff:

```markdown
## Local verification
- [x] Citizen approved the working preview
- [x] Lint, formatting, types, tests, and type-specific execution passed
- [x] Container image built locally, or the approved plan records the replacement gate

## Internal delivery status
Ready for Jenkins, registry, security, and Kubernetes integration. Not yet deployed.
```

Open the pull request and record its real HTTPS URL:

```bash
PR_URL=$(gh pr create --title "Build <app name>" --body-file .plan/PR_BODY.md --base main --head codex/build-initial-app)
uv run .agents/skills/citizen-app/scripts/state.py record-pr --url "$PR_URL"
uv run .agents/skills/citizen-app/scripts/state.py advance
```

Tell the citizen their application is ready for the internal delivery team and
give them the link. Explain that the page shows the reviewed change and its
checks; do not describe either artifact as already operating in the corporate
platform.
