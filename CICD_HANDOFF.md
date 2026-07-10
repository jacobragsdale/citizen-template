# CI/CD artifact handoff

This is the implementation brief for the developer who can access the internal
build platform. It narrows the broader work in
[`CORPORATE_INTEGRATION.md`](CORPORATE_INTEGRATION.md) to the two files that a
generated application should contribute to the corporate build: `Dockerfile`
and `build.yaml` (the latter name is provisional until the internal contract
confirms its exact name and location).

The intended design is deliberately small: platform details live in reviewed
templates in this repository, while the citizen-app workflow selects a template
and supplies only values that are genuinely application-specific. The agent
must not compose CI/CD files from memory or infer corporate infrastructure.

## Current handoff

Today the workflow stops at a pull request and does the following:

- selects a dashboard or automated-job Dockerfile from
  `.agents/skills/citizen-app/assets/dockerfiles/`;
- copies it to the generated repository as `Dockerfile`;
- builds and inspects the image locally;
- binds that image evidence to the project and Dockerfile fingerprints; and
- opens a pull request described as ready for the internal delivery pipeline,
  not deployed.

The current Dockerfiles are useful local placeholders. They use the public
`ghcr.io/astral-sh/uv:python3.11-bookworm-slim` image, run a Streamlit dashboard
on port 8501 or run `python -m app.job` once, and do not contain internal
registry, certificate, identity, scanning, or deployment details.

The missing pieces are:

- no `build.yaml` template or generated file;
- no verified internal base/build image or immutable digest;
- no known internal `build.yaml` schema, discovery rule, or validation command;
- no approved registry/repository naming rule;
- no verified CA, proxy, runtime-user, filesystem, or platform hardening rules;
- no build-platform contract for scans, signing, provenance, status checks, or
  secret references;
- no contract test against the internal system; and
- no stale-evidence check for `.dockerignore` or the future `build.yaml`.

## Target outcome

Every generated application pull request contains a complete, internally valid
`Dockerfile`, `.dockerignore`, and build descriptor. The workflow renders these
files deterministically from repo-owned, platform-reviewed templates.

The application-building agent should only:

1. select `ui` or `job` from the approved workflow state;
2. pass values already known from workflow or repository state; and
3. stop with a clear maintainer-facing error if a required value is absent.

It should not choose base images, registry paths, pipeline libraries, security
steps, credentials, cluster details, or arbitrary build commands. Those are
platform decisions that belong in the templates.

The pull request remains the citizen workflow's finish line for this change.
Extending the workflow through image publication or deployment is separate work
and still requires the evidence model described in `CORPORATE_INTEGRATION.md`.

## Proposed repo-owned contract

Use one delivery asset set so the Dockerfile and build descriptor cannot drift
apart. Adapt names only if the internal system imposes a specific convention.

```text
.agents/skills/citizen-app/
├── assets/
│   └── delivery/
│       ├── ui/
│       │   ├── Dockerfile.template
│       │   └── build.yaml.template
│       ├── job/
│       │   ├── Dockerfile.template
│       │   └── build.yaml.template
│       └── dockerignore
├── scripts/
│   └── render_delivery.py
└── stages/
    └── 09-containerize.md
tests/
├── fixtures/delivery/
│   ├── ui/
│   └── job/
└── test_render_delivery.py
```

If the internal `build.yaml` is identical for both types, keep one shared
template rather than duplicating it. If the internal standard supplies the
Dockerfile or build descriptor through another mechanism, record that evidence
below before changing this layout.

`render_delivery.py` should be the only supported way to produce the files. It
should:

- read `app_name`, `app_type`, and repository data from persisted workflow
  state where possible;
- accept only an explicit allowlist of additional values;
- validate value types, formats, and allowed characters before rendering;
- use a strict token format and fail on missing or unknown tokens;
- write the exact filenames and paths required by the internal system;
- fail if any unresolved token remains in generated output;
- never accept or render a credential, token, certificate private key, or
  secret value; and
- produce byte-for-byte deterministic output for the same inputs.

Prefer a standard-library renderer or another small deterministic mechanism.
Do not require the language model to edit YAML or Dockerfile text directly.

## Minimum-value budget

The internal examples determine the final allowlist. Start from this budget and
add a field only when a verified platform contract proves it cannot be derived
or fixed in a template.

| Candidate value | Expected source | Agent action | Status |
|---|---|---|---|
| Application slug | `state.app_name` | Derive; do not ask again | Confirm internally |
| Application type | `state.app_type` (`ui` or `job`) | Select the matching template | Confirm internally |
| Repository URL or ID | Repository adapter/state | Derive after repository creation | Confirm whether required |
| Owning team ID | Approved plan or repository metadata | Supply only if the build schema requires it | Internal decision required |
| Cost center/data classification | Approved corporate metadata source | Supply only if mandatory and validated | Internal decision required |
| Runtime configuration names | Approved plan; names only | Supply only if the descriptor declares names | Internal decision required |
| Schedule/timezone | Approved job plan | Keep out of build metadata unless the platform requires it | Internal decision required |

The goal is zero manually entered CI/CD values for ordinary applications, or at
most one or two corporate metadata identifiers. A new generated value requires
a documented source, validation rule, owning team, and reason it cannot be
baked into or derived by the template.

The following values should normally be template-owned and invisible to the
application-building agent:

- builder and runtime image references, including immutable digests;
- internal registry host and repository mapping rules;
- Python/uv installation and frozen-sync commands;
- test, scan, SBOM, signing, and provenance steps;
- corporate CA/proxy installation mechanism;
- runtime UID/GID, permissions, capabilities, and filesystem policy;
- build-platform library/plugin identifiers and versions;
- status-check names, artifact retention, and promotion rules; and
- credential or secret-reference wiring.

## Internal contract record

Complete this section from inside the corporate network. Link authoritative
documentation or a passing internal build for every answer. Do not paste
credentials, secret values, private certificates, or sensitive log output.

### Provenance

- Contract owner/team: `[internal decision required]`
- Developer completing this record: `[name required]`
- Verified on: `[YYYY-MM-DD required]`
- Build-platform documentation: `[internal link required]`
- Container-standard documentation: `[internal link required]`
- Passing dashboard reference build: `[internal link or build ID required]`
- Passing automated-job reference build: `[internal link or build ID required]`
- Platform owner who reviewed the templates: `[name/team required]`

### File discovery and schema

- Exact descriptor filename, case, and repository path:
  `[internal decision required]`
- System that consumes it and how repository discovery is triggered:
  `[internal decision required]`
- Published schema/version or canonical example:
  `[internal link required]`
- Approved local validation/lint command:
  `[internal command required]`
- Required versus optional top-level fields:
  `[internal decision required]`
- Whether dashboard and job descriptors differ:
  `[internal decision required]`
- Whether a Jenkinsfile/shared-library entry point is also required:
  `[internal decision required]`

### Image build contract

- Approved builder image and immutable digest:
  `[internal value required]`
- Approved runtime image and immutable digest, if separate:
  `[internal value required]`
- Supported CPU architecture(s): `[internal decision required]`
- Internal dependency mirror and uv configuration mechanism:
  `[internal decision required]`
- Corporate CA/proxy injection mechanism:
  `[internal decision required]`
- Required runtime UID/GID and ownership rules:
  `[internal decision required]`
- Read-only filesystem, capabilities, and security-context expectations:
  `[internal decision required]`
- Dashboard port, startup command, and health contract:
  `[internal decision required]`
- Job command, exit-code, retry, and termination contract:
  `[internal decision required]`
- Required image labels/annotations:
  `[internal decision required]`

### Pipeline contract

- Registry/repository naming rule: `[internal decision required]`
- Immutable tagging/digest rule: `[internal decision required]`
- Required checks and exact published check names:
  `[internal decision required]`
- Required source, dependency, secret, license, and image scans:
  `[internal decision required]`
- SBOM, signing, and provenance requirements:
  `[internal decision required]`
- Approved credential/secret-reference mechanism, names only:
  `[internal decision required]`
- Pull-request versus default-branch behavior:
  `[internal decision required]`
- Artifact retention and build-log link behavior:
  `[internal decision required]`
- Plain-language failure information safe to show citizens:
  `[internal decision required]`

## How to turn the internal facts into templates

1. Obtain sanitized files from one currently passing dashboard and one passing
   automated job. Use the closest supported Python/uv examples, not a generic
   corporate sample.
2. Verify each file against the internal specification and its successful build
   run. A copied file without passing evidence is only a lead.
3. Diff the two examples. Classify each differing value as:
   **platform invariant**, **application-type invariant**, **derivable
   application metadata**, or **required user/corporate metadata**.
4. Put platform invariants directly in the reviewed template. Split UI/job
   templates only for real type differences. Create a token only for the last
   two categories.
5. For every token, record its source and validator in the minimum-value table.
   Remove tokens whose values can be derived from state or repository metadata.
6. Review the proposed templates and token allowlist with the platform owner.
   Record the reviewer and date above.
7. Add sanitized golden outputs and renderer tests before changing the workflow
   stage. Golden fixtures must contain no internal credential or secret.
8. Render and validate both app types locally, then run disposable internal
   pull-request builds. Record links or build IDs in the provenance section.

Do not preserve a placeholder simply because a reference project varies there.
First determine whether the variation is historical noise, a repository-derived
value, or a real application input.

## Workflow changes after the contract is verified

Once the internal record is complete and both golden files pass review:

1. Add the delivery assets and strict renderer.
2. Change `09-containerize.md` to invoke the renderer instead of copying a
   Dockerfile directly.
3. Extend the container/delivery fingerprint in `state.py` to cover at least
   `Dockerfile`, `.dockerignore`, the build descriptor, and the existing project
   fingerprint. Any change must make recorded image evidence stale.
4. Extend `validate.py` to run the approved descriptor validator and safe static
   checks. Keep the local image build until a verified CI evidence command is
   implemented and approved as its replacement.
5. Update the pull-request body to state which delivery contract/template
   version was rendered and which local checks passed.
6. Update `CORPORATE_INTEGRATION.md` with verified decisions, while keeping its
   deployment work open until deployment evidence exists.

Do not modify generated CI/CD files during the application build stage. Render
them from approved inputs during containerization so their creation, validation,
image result, and stale-evidence behavior stay together.

## Required tests

At minimum, add tests that prove:

- UI state selects the UI asset set and job state selects the job asset set;
- a known input renders the reviewed golden Dockerfile and build descriptor
  byte for byte;
- rendering is deterministic;
- missing, unexpected, malformed, or unsafe values fail before files are
  written;
- no unresolved template token can reach a generated repository;
- secret values are not accepted as renderer inputs;
- the descriptor passes the approved internal validator;
- both rendered Dockerfiles build with the approved internal build mechanism;
- changing `Dockerfile`, `.dockerignore`, or the build descriptor invalidates
  prior image/delivery evidence; and
- the citizen-facing completion message still says the pull request is ready
  for internal delivery, not live or deployed.

Run the repository's focused tests plus the full local gates after implementation:

```bash
uv run pytest tests/test_render_delivery.py tests/test_state.py -q
uv run pre-commit run --all-files
uv run pytest
```

The internal contract tests may need a separate network marker, but their last
passing run URL or ID must be recorded before the templates are enabled for
citizen-generated repositories.

## Acceptance checklist

- [ ] Internal contract record is complete and evidence-linked.
- [ ] Platform owner approved both app-type outputs and the token allowlist.
- [ ] Exact build descriptor filename and schema are verified.
- [ ] Templates contain platform decisions; the agent does not invent them.
- [ ] Ordinary generation needs no more than the justified minimum values.
- [ ] Renderer fails closed on missing, unknown, unsafe, or unresolved values.
- [ ] Dashboard and job golden outputs pass the internal validator and build.
- [ ] Delivery files participate in stale-evidence detection.
- [ ] No secrets or private corporate artifacts are committed.
- [ ] Full pre-commit and pytest gates pass.
- [ ] Disposable internal PR builds pass for both app types.
- [ ] The workflow still makes no unverified deployment claim.

## Out of scope for this handoff

This task does not add image publication, environment deployment, schedules,
production approval, rollback, repository-provider adapters, or post-PR state
stages. Those remain in `CORPORATE_INTEGRATION.md` and should be implemented only
after their internal APIs and evidence contracts are verified.
