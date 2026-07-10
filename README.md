# Citizen App Template

Turn a plain-language idea into a locally previewed, tested application that is
ready to enter a corporate delivery pipeline. The workflow handles the code,
checks, container packaging, git branch, and pull request.

It does **not** claim that a pull request is a deployed application. Your
internal Azure DevOps or GitHub Enterprise, Jenkins, registry, and Kubernetes
integration completes that final delivery step.

## Start here

Open this folder in Codex and say something like:

> Help me make a dashboard that shows weekly sales by region.

Codex can select the bundled skill automatically. To select it explicitly,
start the request with `$citizen-app`.

The assistant will:

1. check the required tools before asking you to invest time;
2. ask a few plain-language questions at a time;
3. show you a short plan and wait for your approval;
4. build the app and show you a working preview;
5. revise it until you approve the result you can actually see;
6. run lint, type, test, render, and container checks; and
7. open a pull request ready for the internal delivery pipeline.

You never need to type git, package, Docker, or pull-request commands. You can
stop and resume later; the workflow records where it left off.

## What you can build

- **A dashboard** — a browser page with filters, inputs, tables, and charts.
- **An automated job** — work that runs unattended on a schedule, such as a
  report or data refresh.

The template includes deterministic stocks and bonds sample sources so a
citizen can see a realistic first preview before corporate connections are
available. Their stable data-source interface is the seam for replacing sample
data with internal APIs or databases later.

## What “finished” means

Before the workflow opens a pull request, the application has been previewed
with representative data, approved by the citizen, tested against its success
criteria, and packaged for the corporate container platform.

The pull request is the deliberate handoff point. It is ready for internal CI,
security scanning, registry publication, and Kubernetes deployment, but it is
not described as live until those systems confirm deployment.

See [CORPORATE_INTEGRATION.md](CORPORATE_INTEGRATION.md) for the
network-only work required to connect the template to your organization.

## For maintainers

This is a Python 3.11, uv-managed template repository. The reusable workflow
lives only in `.agents/skills/citizen-app/`; `AGENTS.md` is the canonical set of
repository instructions.

Run all local checks with:

```bash
uv run pre-commit run --all-files
uv run pytest
```

### Running an application

The build stage replaces this section in each generated application with its
actual preview and one-off run commands.
