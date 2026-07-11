# Citizen template improvement plan

Status: active; first Windows-driven P0/P1 tranche implemented

## Purpose

This document is the program-level improvement plan for the citizen template.
It covers the workflow, state machine, generated applications, evidence,
validation, packaging, and citizen-facing experience.

The [Windows no-admin test harness plan](WINDOWS_TEST_HARNESS_PLAN.md) is a
supporting test-infrastructure plan. It should prove these improvements on
fresh standard-user Windows machines, but it is not a substitute for fixing the
program itself.

## Current assessment

The core design is sound:

- the workflow moves a nontechnical user from an idea to a reviewed plan;
- plan, build, preview, validation, container, and PR evidence are revision
  fingerprinted;
- stale plan, build, preview, and validation evidence is rejected;
- documented rewinds recover deterministically;
- dashboard and job starters support a functional-core/imperative-shell split;
- the preconfigured data-source seam works for both application types;
- local drafts do not accidentally publish code;
- the PR remains an honest corporate-delivery handoff rather than a deployment
  claim.

Three independent Windows runs reached the intended `ship` boundary and
produced working dashboard and job images. The same runs found correctness and
portability gaps that should be fixed before broader citizen use.

## Implemented foundation

The first tranche now includes explicit UTF-8 repository boundaries,
file/stdin structured state input, fingerprinted build-check evidence,
application-test filtering, richer preview summaries, an external
fingerprint-bound container verifier, and type-specific container runtime
smoke checks. The repo-owned Windows harness exercises these contracts as a
fresh standard user with staged portable tools.

Live disposable-VM proof now includes complete job and dashboard workflows at
8 GB, controller-browser review of the dashboard, external Linux image runtime
checks for both application types, and a successful 4 GB bootstrap stress run.

This does not close the program plan. Local completion semantics, citizen-facing
diagnostic cleanup, broader generated-project helpers, the full failure matrix,
and the 20-run reliability proof remain follow-up work.

## Program goals

- Make every workflow gate prove what its name claims.
- Support macOS, Linux, and standard-user Windows without shell-specific agent
  improvisation.
- Keep citizen approval tied to meaningful, visible application behavior.
- Make failures actionable without exposing raw engineering noise.
- Preserve strong stale-evidence and resume behavior.
- Verify that built images actually execute.
- Distinguish successful local completion from published PR completion.
- Keep corporate provider and deployment assumptions outside the generic
  workflow until their contracts are verified.

## Non-goals

- Claiming that a PR is deployed.
- Inventing corporate repository, Jenkins, registry, or Kubernetes details.
- Weakening local checks because a platform integration is unavailable.
- Making Docker installation part of the citizen experience.
- Turning the stage Markdown into an untestable collection of shell snippets.
- Supporting arbitrary application frameworks before dashboard and job paths
  are reliable.

## Priorities

| Priority | Workstream | Reason |
|---|---|---|
| P0 | Explicit UTF-8 boundaries | Windows validation currently fails on normal non-ASCII content |
| P0 | Trustworthy build evidence | `record-build` can advance code with known lint/type failures |
| P0 | Application-specific acceptance tests | Bundled workflow tests can satisfy the current structural test check |
| P1 | Shell-neutral workflow operations | Required Bash examples do not execute reliably in PowerShell |
| P1 | Structured state input | Positional JSON is fragile across shells and native process boundaries |
| P1 | Acceptance-aware preview evidence | Existing summaries omit important controls, metrics, and behaviors |
| P1 | Container runtime verification | A successful image build does not prove its command starts correctly |
| P1 | Capability-aware preflight | Tool presence is not the same as a usable engine, browser, or provider session |
| P2 | Local completion semantics | A successful local rehearsal currently looks permanently blocked at `ship` |
| P2 | Citizen-facing diagnostic cleanup | Unicode corruption and benign warnings make successful output look broken |

## Workstream 1 — make text handling deterministic

### Problem

Python's default text encoding differs by platform. On Windows, inherited tests
and preview evidence used cp1252, which broke UTF-8 Markdown, corrupted Unicode
evidence, and produced invalid generated Python source.

### Changes

- Audit every `Path.read_text`, `Path.write_text`, `open`, subprocess text
  boundary, and generated evidence file.
- Specify `encoding="utf-8"` for repository-owned text.
- Use `errors="strict"` for source, plans, state-adjacent evidence, and test
  fixtures so corruption fails immediately.
- Keep raw external command bytes in diagnostic logs when decoding is uncertain;
  create a separately normalized citizen-facing summary.
- Make CLI messages reliably UTF-8 across supported terminals or use ASCII
  punctuation where encoding adds no value.
- Add non-ASCII plan titles, requirements, preview output, and source fixtures
  to regression tests.

### Exit criteria

- The complete suite passes on Windows with the default en-US locale.
- A plan, README, and job output containing non-ASCII punctuation survive every
  workflow stage byte-for-byte.
- No run-local encoding patch is required.

## Workstream 2 — make the build gate truthful

### Problem

`record-build` checks file shape and fingerprints but does not require current
lint, formatting, type, or application-test results. A stress run advanced to
preview with known Ruff and basedpyright failures.

The structural test check can also count bundled workflow tests rather than
proving that the generated application has acceptance-specific behavior tests.

### Changes

Create a build helper that runs and records:

- Ruff lint;
- Ruff formatting check;
- basedpyright;
- focused application tests;
- entry-point import or dry render;
- required file and placeholder checks.

Add state evidence similar to:

```text
record-build-checks \
  --evidence .plan/build/summary.json \
  --application-test tests/test_<application>.py
```

The evidence must contain:

- the project fingerprint;
- the approved plan fingerprint;
- exact commands and exit codes;
- named application-test files and collected test names;
- timestamp and schema version;
- an overall passing result.

`record-build` should either be replaced by this command or require its current
passing evidence. It must reject:

- missing or stale evidence;
- a different plan or project fingerprint;
- zero application-specific tests;
- only template/workflow contract tests;
- lint, formatting, type, import, or test failures.

### Exit criteria

- A deliberate lint, type, import, or application-test failure cannot advance
  past `build`.
- Fixing the issue and rerunning the helper advances normally.
- Stale build evidence is rejected after any project change.

## Workstream 3 — replace shell-sensitive required operations

### Problem

The stage playbooks contain required Bash commands for copying starters,
setting JSON, calculating image tags, and inspecting Docker images. PowerShell
required manual translations and special quoting.

### Changes

Move required deterministic operations into Python entry points under the
skill's `scripts/` directory:

```text
project.py create-local --name ... --destination ...
project.py apply-starter --type ui|job
project.py set-identity --name ...
state.py set-json requirements --file requirements.json
state.py set-json requirements --stdin
container.py build --tag ...
container.py verify --tag ...
```

The Markdown playbooks should describe decisions and call these helpers. They
should not implement required workflow behavior with shell-specific pipelines,
command substitution, or quoting.

For commands that remain illustrative, provide tested Bash and PowerShell
variants.

### Design requirements

- JSON and other structured values travel through files or stdin, not complex
  positional arguments.
- Helpers emit stable machine-readable JSON on stdout and diagnostics on
  stderr.
- Paths with spaces and non-ASCII characters are supported.
- Operations are idempotent or fail with a clear existing-state message.
- No helper mutates `.plan/state.json` except through the state authority.

### Exit criteria

- Dashboard and job golden paths run unchanged from Bash and PowerShell.
- No stage requires stop-parsing syntax or hand-built quoting.
- A workspace under `Citizen Apps\café demo` completes validation.

## Workstream 4 — make preview evidence reflect approval

### Problem

The current dashboard preview helper proves that Streamlit rendered, but its
summary reports only a small subset of widget types. It can omit the numeric
input, multiselect, metric, warning, and charts that define the application's
success criteria.

An automated render is also different from a citizen seeing and approving the
real page. Browser capability may be unavailable even when AppTest passes.

### Changes

- Expand generic UI evidence to include:
  - titles and headings;
  - text, numeric, date, select, and multiselect inputs;
  - buttons and toggles;
  - metrics;
  - tables and dataframes;
  - charts;
  - warnings, errors, empty states, and exceptions.
- Store structured JSON alongside the human summary.
- Allow each generated application to provide acceptance-specific AppTest
  assertions without editing the workflow helper.
- Record representative control interactions and resulting visible values.
- Check browser availability before asking for citizen preview approval.
- Separate these evidence concepts:
  - `render_passed` — automated page execution;
  - `browser_reviewed` — the actual page was available to the reviewer;
  - `preview_approved` — the citizen explicitly approved that revision.
- Preserve full diagnostic output but filter known benign Streamlit warnings
  from the citizen-facing summary.

### Exit criteria

- The stocks threshold scenario records the numeric input and changed result
  metric.
- The comparison dashboard records its multiselect, metrics, and charts.
- A missing browser blocks only the citizen-visible approval step and explains
  what evidence is still available.
- Approval remains bound to the exact application fingerprint.

## Workstream 5 — strengthen validation evidence

### Problem

Validation currently runs the right broad checks, but its evidence is primarily
a flat pass/fail summary. Maintainers need enough structured data to identify
the exact failed contract and prove evidence belongs to the current revision.

### Changes

- Write a versioned JSON validation artifact in addition to `summary.txt`.
- Record command, exit code, duration, and diagnostic-log path for every check.
- Record collected and passed application-test names separately from workflow
  contract tests.
- Record the project and plan fingerprints inside the evidence file.
- Keep citizen summaries short; keep full output in diagnostic logs.
- Make retry behavior deterministic and clear previous evidence before a new
  validation attempt.
- Add failure-injection tests for every validation component.

### Exit criteria

- State rejects manually edited, incomplete, failed, stale, or wrong-revision
  validation artifacts.
- A maintainer can identify the failing check from the summary without parsing
  an entire console transcript.
- A citizen sees what failed, what it affects, and what happens next.

## Workstream 6 — prove the image actually works

### Problem

The container stage records a build and image ID but does not run the image.
A broken `CMD`, missing runtime dependency, wrong port, or job entry point can
pass the current gate.

### Changes

Create a container helper that:

1. copies or verifies the correct Dockerfile and ignore file;
2. builds the image;
3. polls `docker image inspect` until the image ID is available or a bounded
   timeout expires;
4. runs a type-specific smoke check;
5. writes versioned evidence;
6. records the image only after all checks pass.

Dashboard smoke behavior:

- run the container on an available local port;
- poll Streamlit health;
- optionally load the page through AppTest or HTTP;
- stop and remove the test container;
- retain relevant logs on failure.

Job smoke behavior:

- run the container once with representative configuration;
- require exit code 0;
- require non-empty expected output;
- prove dry-run or delivery suppression when irreversible delivery exists.

Support both local and external verification evidence. External evidence must be
bound to the exact project and Dockerfile fingerprints as described in the
[Windows harness plan](WINDOWS_TEST_HARNESS_PLAN.md).

### Exit criteria

- A deliberately broken dashboard command and job entry point are rejected.
- Both golden applications build and pass runtime smoke checks.
- A source or Dockerfile change invalidates prior container evidence.

## Workstream 7 — make preflight capability-aware

### Problem

Executable presence is not enough. Docker Desktop can be installed while its
engine is unavailable. A browser can be missing when preview begins. A provider
CLI can exist without usable authentication.

### Changes

Preflight should return structured capability results:

```json
{
  "python_project_tools": "ready",
  "git": "ready",
  "browser": "missing",
  "container_engine": "installed_not_ready",
  "repository_provider": "local_only"
}
```

Distinguish:

- executable missing;
- executable present but command failed;
- authentication missing;
- engine or service starting;
- policy or permission blocked;
- capability deliberately externalized;
- capability ready.

Docker readiness should use bounded `docker info` retries rather than process
or UI status. Windows diagnostics should explain the difference between a
per-user Docker installation and a machine where WSL 2 is not enabled.

Browser readiness should be checked before the preview stage, not after the
server is already running.

### Exit criteria

- Every missing capability produces one actionable plain-language diagnosis.
- The workflow knows before interview which finish lines are locally possible.
- A temporarily starting engine can become ready without rerunning scaffold by
  hand.

## Workstream 8 — add honest local completion

### Problem

A local draft can complete plan approval, build, preview approval, validation,
and container verification, then remain at `ship` with a permanent blocked
message because no repository adapter exists. This is safe but reads like a
failed application rather than a successful local rehearsal.

### Changes

Add a distinct local completion state or outcome, such as `local-ready`, with
language that says:

- the application is locally reviewed and verified;
- no repository or PR was created;
- the source and evidence are preserved;
- a repository adapter is required before corporate handoff.

Do not make `local-ready` equivalent to `done`. `done` continues to require the
real PR and corporate-delivery handoff defined by the workflow.

Possible transition:

```text
containerize -> local-ready
containerize -> ship -> done
```

The state command should allow a local-ready application to resume at `ship`
after a repository adapter becomes available without repeating current
evidence unless the project changed.

### Exit criteria

- Local test drives finish with a successful, non-deployment claim.
- PR-backed runs retain the existing `ship` and `done` semantics.
- Resuming a current local-ready revision for publication is deterministic.

## Workstream 9 — improve generated application contracts

The rehearsals showed the generated apps were easier to validate than the
workflow itself. Preserve that strength and make it explicit.

Every generated application should have:

- a pure or nearly pure `core.py` containing decisions and calculations;
- a thin UI or job entry point;
- named tests mapped to acceptance criteria;
- representative sample data clearly labeled as sample data;
- empty, invalid-input, and source-failure behavior;
- configuration documented without secret values;
- a real job dry-run path where relevant;
- a README with working commands for the supported platform;
- no instructional placeholders after build;
- one type-specific runtime contract that the container smoke test can call.

Add a machine-readable acceptance mapping under `.plan/`, for example:

```json
{
  "criterion": "A user can compare several stock symbols",
  "tests": ["tests/test_stock_dashboard.py::test_multiple_symbols_are_compared"],
  "preview_assertions": ["comparison_symbol_count"]
}
```

The first version can be agent-generated and validated structurally. Do not
attempt automatic natural-language proof.

## Workstream 10 — maintainer testing strategy

### Unit and contract tests

Add focused tests for:

- explicit encodings;
- structured state input;
- build-check evidence;
- app-specific test detection;
- expanded preview evidence;
- browser capability states;
- container build and runtime evidence;
- local-ready transitions;
- stale and forged evidence for every new artifact.

### Golden-path integration tests

Maintain four deterministic scenarios:

1. dashboard happy path;
2. automated-job happy path;
3. revision and rewind stress path;
4. local-ready to later ship/resume path.

Run them on Linux and Windows. Use the
[Windows no-admin harness](WINDOWS_TEST_HARNESS_PLAN.md) for fresh-machine
release evidence.

### Failure injection

Each stage should have at least one deliberate failure:

- missing prerequisite;
- invalid structured input;
- stale plan;
- failed lint/type/application test;
- render exception;
- unavailable browser;
- failed validation component;
- image build failure;
- broken container entry point;
- provider unavailable or PR URL rejected.

Prove both the error message and the documented recovery.

## Implementation sequence

### Phase 1 — correctness first

- Complete the UTF-8 audit and Windows regression tests.
- Implement build-check evidence and application-test detection.
- Prevent broken builds from reaching preview.

Exit criterion: a clean Windows run reaches preview without run-local patches,
and deliberate build failures cannot advance.

### Phase 2 — portable workflow operations

- Add file/stdin-based structured state input.
- Add project and starter helpers.
- Remove required Bash-only operations from stage playbooks.
- Test paths containing spaces and non-ASCII characters.

Exit criterion: dashboard and job builds use the same documented commands in
Bash and PowerShell.

### Phase 3 — meaningful preview and validation

- Expand UI evidence and application-specific assertions.
- Add browser capability handling.
- Add structured validation evidence and diagnostic separation.

Exit criterion: preview approval is supported by evidence tied to each
application's critical controls and results.

### Phase 4 — runtime packaging proof

- Implement container build polling and type-specific runtime smoke checks.
- Add fingerprinted external verification evidence.
- Integrate the no-admin Windows lane.

Exit criterion: both application types reject broken runtime commands and pass
locally or through an approved external builder.

### Phase 5 — completion and experience polish

- Add local-ready semantics.
- Normalize citizen-facing output and warnings.
- Improve progress, recovery, and handoff summaries.

Exit criterion: local and PR-backed runs have distinct, honest, understandable
finish lines.

### Phase 6 — corporate adapters

Implement only after the internal contracts in
[CORPORATE_INTEGRATION.md](CORPORATE_INTEGRATION.md) and
[CICD_HANDOFF.md](CICD_HANDOFF.md) are filled with verified facts.

Do not couple the generic correctness work above to an unverified provider.

## Likely file ownership

| Area | Owning files |
|---|---|
| State and evidence | `.agents/skills/citizen-app/scripts/state.py` plus new evidence helpers |
| Preflight | `.agents/skills/citizen-app/scripts/preflight.py` |
| Preview | `.agents/skills/citizen-app/scripts/preview.py` |
| Validation | `.agents/skills/citizen-app/scripts/validate.py` |
| Project operations | new `.agents/skills/citizen-app/scripts/project.py` |
| Container verification | new `.agents/skills/citizen-app/scripts/container.py` |
| Stage decisions and citizen language | `.agents/skills/citizen-app/stages/*.md` |
| Starter contracts | `.agents/skills/citizen-app/assets/` |
| Unit and contract tests | `tests/` |
| Fresh Windows evidence | `tools/windows-harness/` and the external home-server adapter |

Keep `.agents/skills/citizen-app/` as the single workflow source of truth.
Harness code may invoke the workflow but must not reimplement its stage rules.

## Definition of done

The improvement program is complete when:

- Linux, macOS, and standard-user Windows golden paths pass;
- repository text and evidence are explicitly UTF-8;
- build cannot advance without current lint, format, type, import, and
  application-test evidence;
- required operations are shell-neutral;
- structured state input does not depend on quoting JSON;
- preview evidence covers acceptance-critical controls and results;
- browser review and automated render evidence are distinguished;
- validation evidence is structured and revision-bound;
- dashboard and job images pass runtime smoke tests;
- stale or forged evidence is rejected at every gate;
- local runs finish as `local-ready` without claiming publication;
- PR-backed runs retain the existing corporate handoff definition;
- all failure paths have tested recovery;
- the Windows harness completes at least 20 fresh standard-user runs without a
  run-local workaround.

## Recommended first milestone

Implement these items together as the first reviewable milestone:

1. explicit UTF-8 on every workflow and test text boundary;
2. Windows regression coverage for non-ASCII plans and preview evidence;
3. a build-check helper with fingerprinted lint, type, and application-test
   results;
4. state rejection when current build-check evidence is missing or failed.

This milestone fixes the two highest-risk correctness defects without waiting
for the broader harness, preview, container, or corporate-integration work.
