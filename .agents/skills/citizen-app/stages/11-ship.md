# Stage 11 — publish the corporate-ready pull request

Goal: put the approved, validated, container-ready revision in a pull request
for the internal delivery pipeline. This is the corporate handoff finish line.

Read `repo_provider` from state. The currently implemented provider is GitHub
through `gh`. Azure DevOps or an unverified enterprise provider must stop here
and follow `CORPORATE_INTEGRATION.md`; never publish to a personal public
repository as a fallback.

## GitHub provider

Create or resume a `codex/` branch, commit only the intended app changes, and
push it. Write `.plan/PR_BODY.md` from the approved plan and include:

```markdown
## Local verification
- [x] Citizen approved the working preview
- [x] Lint, formatting, types, tests, and type-specific execution passed
- [x] Container image passed its type-specific runtime smoke check

## Internal delivery status
Ready for Jenkins, registry, security, and Kubernetes integration. Not yet deployed.
```

Open the pull request with the configured provider, then record its real HTTPS
URL and advance:

```text
uv run .agents/skills/citizen-app/scripts/state.py record-pr --url <pull-request-url>
uv run .agents/skills/citizen-app/scripts/state.py advance
```

Tell the citizen their application is ready for the internal delivery team and
give them the link. Do not describe the pull request as a live application.
