# Stage 09 — containerize

Goal: create the portable image artifact expected by the future internal
Jenkins and Kubernetes integration and prove it builds locally.

Tell the citizen before starting: packaging can take several minutes and they
can step away while you keep working.

The helper selects or verifies the matching Dockerfile and ignore file, builds,
inspects, and runs the type-specific smoke check. Its default tag comes from the
current folder, so the command is unchanged across Bash and PowerShell:

```text
uv run .agents/skills/citizen-app/scripts/container.py
uv run .agents/skills/citizen-app/scripts/state.py advance
```

On a no-admin Windows machine, the approved external verifier runs the same
helper with `--no-record`, returns `.plan/container/verification.json`, and the
guest records it with:

```powershell
uv run .agents/skills/citizen-app/scripts/state.py record-container-verification --evidence .plan/container/verification.json
uv run .agents/skills/citizen-app/scripts/state.py advance
```

The public base image is a development placeholder. Do not invent an internal
registry, CA bundle, proxy, scan, signature, or runtime identity. Those choices
are explicit tasks in `CORPORATE_INTEGRATION.md`.

If local image builds are deliberately unavailable, use fingerprinted external
verification. Setting `container.required` to `false` remains an infrastructure
decision for a verified corporate CI replacement, not a convenience escape
from a failing build.
