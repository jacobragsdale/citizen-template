# Stage 07 — containerize (build gate)

Goal: package the app into a container image and prove it builds. (Pushing to
ACR and deploying to Kubernetes happen later — not here.)

## Do this

1. Put the matching Dockerfile and a .dockerignore at the repo root:

   **UI:**
   ```bash
   cp .claude/skills/citizen-app/assets/dockerfiles/Dockerfile.ui Dockerfile
   ```
   **Job:**
   ```bash
   cp .claude/skills/citizen-app/assets/dockerfiles/Dockerfile.job Dockerfile
   ```
   ```bash
   printf '.git\n.venv\n__pycache__/\n.plan/\n.env\n.env.*\n!.env.example\n' > .dockerignore
   ```

2. Build the image locally to prove it works:
   ```bash
   docker build -t "$(basename "$PWD"):local" .
   ```
   If it fails, read the error, fix the cause (usually a missing dependency —
   add it with `uv add`, which updates `uv.lock` so the frozen install inside
   the image succeeds), and rebuild. Explain any failure to the citizen plainly.

3. Only once the build succeeds:
   ```bash
   uv run .claude/skills/citizen-app/scripts/state.py set image_built true
   uv run .claude/skills/citizen-app/scripts/state.py advance
   ```

## Exit gate

`image_built == true`. Set it only after a real successful `docker build` in
this run.
