# Stage 09 — containerize

Goal: create the portable image artifact expected by the future internal
Jenkins and Kubernetes integration and prove it builds locally.

Tell the citizen before starting: packaging can take several minutes and they
can step away while you keep working.

Copy the matching Dockerfile and shared ignore file:

```bash
cp .agents/skills/citizen-app/assets/dockerfiles/Dockerfile.ui Dockerfile
cp .agents/skills/citizen-app/assets/dockerfiles/dockerignore .dockerignore
```

Use `Dockerfile.job` for an automated job.

Build and inspect the image:

```bash
IMAGE_TAG="$(basename "$PWD"):local"
docker build -t "$IMAGE_TAG" .
IMAGE_ID=$(docker image inspect "$IMAGE_TAG" --format '{{.Id}}')
uv run .agents/skills/citizen-app/scripts/state.py record-image --tag "$IMAGE_TAG" --image-id "$IMAGE_ID"
uv run .agents/skills/citizen-app/scripts/state.py advance
```

The public base image is a development placeholder. Do not invent an internal
registry, CA bundle, proxy, scan, signature, or runtime identity. Those choices
are explicit tasks in `CORPORATE_INTEGRATION.md`.

If local image builds are deliberately unavailable in the corporate developer
environment, a maintainer may set `container.required` to `false` and document
the Jenkins replacement gate in the plan. This is an infrastructure decision,
not a convenience escape from a failing build.
