# Citizen App Template

Turn an idea into a running, published application — without needing to know
git, packages, Docker, or pull requests. One command walks you through it.

## Start here

Open this folder in Claude Code and run:

```
/citizen-app
```

The assistant interviews you about what you want to build, writes a plan for
you to approve, builds and tests the app, packages it, and publishes it to
GitHub as a pull request. You never touch git or the terminal yourself.

You can stop any time and rerun `/citizen-app` — it picks up where you left off.

## What you can build

- **A UI** — a web app with buttons, inputs, and charts (built with Streamlit).
- **A scheduled job** — code that runs automatically on a schedule (e.g. a
  nightly report), packaged as a Kubernetes CronJob.

## For maintainers

This is a GitHub **template repository**. Each new app is created from it with
`gh repo create citizen-<name> --template <owner>/<this-repo>`. The uv baseline
(Python 3.11, ruff, basedpyright, pre-commit, `.env` convention) is already set
up; see [AGENTS.md](AGENTS.md). The workflow itself lives in
`.claude/skills/citizen-app/`.

### Running (filled in per app)

| command | what it does |
|---|---|
| _(the build stage adds your app's run command here)_ | |
