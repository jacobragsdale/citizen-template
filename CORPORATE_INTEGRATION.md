# Corporate delivery integration checklist

This repository deliberately stops at a locally verified pull request because
the source-control, Jenkins, registry, secret-management, and Kubernetes systems
are reachable only inside the corporate network.

Complete this file in the network before changing the citizen workflow to claim
deployment. Replace every `<decision required>` with a verified value or link;
never copy credentials, tokens, certificates, or secret values into this repo.

## Completion definition

Integration is complete only when both golden paths pass inside the network:

1. A dashboard PR receives required checks, publishes an approved image, deploys
   to a non-production namespace, and returns a reachable authenticated URL.
2. An automated-job PR receives required checks, publishes an approved image,
   creates or updates its real schedule, completes a manual test run exactly
   once, and exposes failure status to the owning team.

Until then, `done` means “PR ready for the internal delivery pipeline,” not
“application deployed.”

## 1. Record the platform contract

- [ ] Choose the source-control path: Azure DevOps Repos, GitHub Enterprise, or
      both.
- [ ] Record the canonical organization, project, and repository-template IDs:
      `<decision required>`.
- [ ] Record the approved developer authentication mechanism and CLI:
      `<decision required>`.
- [ ] Record repository visibility, ownership, retention, and naming rules:
      `<decision required>`.
- [ ] Record branch naming, protected branches, required reviewers, CODEOWNERS,
      merge strategy, and required status-check names: `<decision required>`.
- [ ] Record the Jenkins controller, approved shared-library name/version, and
      multibranch discovery convention: `<decision required>`.
- [ ] Record the internal container registry/repository naming convention:
      `<decision required>`.
- [ ] Record the Kubernetes management layer (direct API, Argo CD, Flux, custom
      portal/operator, or another system): `<decision required>`.
- [ ] Record the non-production and production approval owners:
      `<decision required>`.

Link internal documentation here after verifying it from inside the network:

- Source control: `<internal link required>`
- Jenkins: `<internal link required>`
- Container platform: `<internal link required>`
- Kubernetes delivery: `<internal link required>`
- Secrets and data classification: `<internal link required>`
- Support/incident ownership: `<internal link required>`

## 2. Implement repository adapters

The current scaffold and ship playbooks support `local` and development
`github` providers. Add deterministic scripts rather than embedding long API
sequences in Markdown.

Create:

- `.agents/skills/citizen-app/scripts/repository.py`

Required interface:

```text
repository.py preflight --provider azure-devops|github-enterprise
repository.py create --provider ... --name ... --visibility ...
repository.py clone --provider ... --repo-url ... --destination ...
repository.py open-pr --provider ... --head ... --base ... --body-file ...
repository.py pr-status --provider ... --url ...
```

Requirements:

- [ ] Return JSON on stdout with stable keys: `provider`, `repo_url`,
      `default_branch`, and, for PR creation, `pr_url`.
- [ ] Send diagnostics to stderr and return nonzero on auth, policy, API, clone,
      or PR failure.
- [ ] Obtain credentials from the approved host credential mechanism; never
      accept secret values as command-line arguments.
- [ ] Require an explicit visibility value and make the corporate-safe option
      the default.
- [ ] Verify the populated template file set after creation to handle eventual
      consistency.
- [ ] Make create/open-PR operations resumable and idempotent.
- [ ] Unit-test response parsing with sanitized provider fixtures and add one
      network-marked contract test per provider.
- [ ] Update `preflight.py`, scaffold, and ship playbooks only after both the
      provider contract tests and a disposable repository rehearsal pass.

## 3. Add the Jenkins contract

Decide whether generated repositories contain a small `Jenkinsfile` or are
discovered and configured entirely by an approved shared library.

- [ ] Add only the minimum repo-owned pipeline entry point required by the
      internal standard.
- [ ] Reproduce the local gates: frozen dependency sync, ruff, basedpyright,
      pytest, dashboard `AppTest` or job dry-run, and image build.
- [ ] Use the internal Python/uv and container base-image mirrors.
- [ ] Install the corporate CA/proxy configuration through the approved build
      mechanism, not by disabling TLS verification.
- [ ] Generate an SBOM and run the required source, dependency, secret, license,
      and image scans.
- [ ] Sign images and attach provenance if required.
- [ ] Push immutable image references; pass digests, not mutable tags, to the
      deployment system.
- [ ] Publish the exact required status-check names recorded in section 1.
- [ ] Define which failures citizens see in plain language and which diagnostics
      remain maintainer-only.
- [ ] Decide whether a passing Jenkins build replaces the local Docker gate; if
      so, extend `state.py` with a verified CI evidence command rather than
      setting `container.required=false` silently.

## 4. Harden container assets

The current Dockerfiles intentionally use the public uv base as a local
placeholder.

- [ ] Replace it with the approved internal image and immutable digest.
- [ ] Apply the required runtime UID/GID, filesystem, capability, seccomp, and
      read-only-root-filesystem policy.
- [ ] Add approved CA certificates without copying private keys or credentials.
- [ ] Confirm supported CPU architectures and build strategy.
- [ ] Record resource and ephemeral-storage expectations.
- [ ] Confirm the dashboard port and job process/exit-code contract.
- [ ] Prove containers start without developer `.env` files.

## 5. Add Kubernetes delivery assets

Choose the organization-standard format: Helm, Kustomize, generated manifests,
an internal application descriptor, or an API call to the management layer.

Shared requirements:

- [ ] Namespace and ownership labels/annotations.
- [ ] Service account and least-privilege RBAC.
- [ ] CPU/memory requests and limits.
- [ ] Approved secret injection through Key Vault, External Secrets, CSI, or the
      corporate equivalent; no raw Kubernetes Secret values in git.
- [ ] Network policy and allowed egress destinations.
- [ ] Logging, metrics, traces, alerts, support contact, and retention.
- [ ] Non-production promotion, production approval, rollback, and cleanup.

Dashboard requirements:

- [ ] Deployment, Service, ingress/route, TLS, authentication, and authorization.
- [ ] Startup, readiness, and liveness probes that execute meaningful behavior.
- [ ] Verified external URL returned by the deployment system.
- [ ] Empty/error behavior tested when dependencies are unavailable.

Automated-job requirements:

- [ ] CronJob or internal scheduler object with explicit timezone behavior.
- [ ] `concurrencyPolicy`, retry/backoff, deadline, suspension, and history limits.
- [ ] Idempotency/duplicate-output protection validated by a retry rehearsal.
- [ ] Manual one-off run mechanism and dry-run mechanism.
- [ ] Failure notification routed to the recorded owner.
- [ ] Verified schedule identity and next-run information returned by the
      deployment system.

## 6. Extend workflow evidence without weakening local gates

After the provider and deployment APIs exist, add these state commands with
tests before inserting new stages:

```text
record-ci --provider ... --run-url ... --commit ... --result passed
record-image-push --digest ... --registry ... --run-url ...
record-deployment --environment ... --deployment-id ... --evidence-url ...
verify-dashboard --url ... --evidence ...
verify-job --schedule-id ... --manual-run-id ... --evidence-url ...
```

Each command must:

- [ ] validate provider URLs and required fields;
- [ ] bind evidence to the exact commit and image digest;
- [ ] reject empty, failed, stale, or different-revision evidence;
- [ ] clear downstream evidence when an upstream revision changes; and
- [ ] have bypass, resume, stale-evidence, and provider-error tests.

Only then extend the stage sequence after `ship`, for example:

```text
ci -> publish-image -> deploy-nonprod -> verify -> handoff
```

Production promotion should remain an explicit corporate approval unless the
organization already has a documented automatic policy.

## 7. Security and governance review

- [ ] Threat-model code/data sent to model or connector services.
- [ ] Confirm which corporate data classifications are permitted in prompts,
      local samples, logs, PR descriptions, and test fixtures.
- [ ] Add secret scanning before commit and in Jenkins.
- [ ] Confirm that repository plans and generated sample data have appropriate
      retention and access.
- [ ] Review dependencies, base images, licenses, and external network egress.
- [ ] Define audit evidence for repository creation, approvals, builds,
      deployments, manual job runs, and rollbacks.
- [ ] Run the required application-security and platform reviews.

## 8. Rehearse before enabling citizens

- [ ] Run a disposable dashboard from idea through authenticated non-production
      URL and rollback.
- [ ] Run a disposable automated job through schedule creation, one manual run,
      retry without duplicate output, failure alert, and cleanup.
- [ ] Interrupt and resume both workflows at every new stage.
- [ ] Revoke/expire credentials and verify that failures are safe and clear.
- [ ] Confirm citizens never need to type a terminal command or see a raw stack
      trace during the golden paths.
- [ ] Have a non-technical pilot user complete both paths and record corrections
      in `.agents/skills/citizen-app/LEARNINGS.md`.
- [ ] Update README’s definition of done only after the evidence-backed
      deployment stages pass these rehearsals.
