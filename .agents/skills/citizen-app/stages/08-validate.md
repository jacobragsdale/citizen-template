# Stage 08 — validate

Goal: prove the approved revision is clean, tested, and executable before
packaging it for the internal pipeline.

Run the complete checker:

```bash
uv run .agents/skills/citizen-app/scripts/validate.py
```

It runs dependency sync, lint, formatting, types, pytest, and the type-specific
preview again. Dashboard validation executes the page with Streamlit `AppTest`;
job validation executes the real dry-run wiring.

The validator writes `.plan/validation/summary.json`, a concise `summary.txt`,
and one UTF-8 diagnostic log per check. The JSON records exact commands, exit
codes, durations, application and workflow tests, and current plan/project
fingerprints. Each retry clears the prior summaries before running.

If anything fails, explain the citizen-visible consequence, rewind to build,
fix the cause without weakening rules or deleting tests, and repeat build,
preview, user approval, and validation.

After `ALL CHECKS PASSED`, advance. The validator records the generated evidence
through `state.py` itself, so the gate is derived from that successful run:

```bash
uv run .agents/skills/citizen-app/scripts/state.py advance
```

Any later application change makes this evidence stale and blocks shipping.
