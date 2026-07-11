# Stage 10 — local-ready

Goal: finish a local-only rehearsal honestly while preserving the reviewed,
validated, runtime-verified revision for later publication.

Tell the citizen:

- the application is locally reviewed and verified;
- its source, plan, and evidence are preserved in this folder;
- no repository, pull request, or deployment was created; and
- a supported repository adapter is required for corporate handoff.

`state.py advance` prints the local completion message and remains at this
stage. Do not call this outcome `done` or imply that delivery occurred.

If a supported repository becomes available later, record its provider,
visibility, and HTTPS repository URL through `state.py set`, then resume the
same current revision:

```text
uv run .agents/skills/citizen-app/scripts/state.py resume-ship
```

The command rejects stale plan, preview, validation, or container evidence. If
the application changed, follow its rewind message and repeat the invalidated
checks instead of forcing publication.
