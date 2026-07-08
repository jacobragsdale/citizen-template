# Stage 04 — plan review (approval gate)

Goal: the citizen reads the plan and explicitly approves it before anything is
built. This is a hard gate.

## Do this

1. Show them `.plan/PLAN.md` in full, then summarize it back in two or three
   friendly sentences — what it will do, what it needs, and what "done" means.
2. Ask directly: "Does this look right, or should I change anything?"
3. If they want changes: edit `.plan/PLAN.md` (and re-run the relevant parts of
   the interview if needed), then show it again. Loop until they are happy.
4. Only when they clearly say yes:
   ```bash
   uv run .claude/skills/citizen-app/scripts/state.py set plan_approved true
   uv run .claude/skills/citizen-app/scripts/state.py advance
   ```

Do NOT set `plan_approved` on a maybe, a "looks fine I guess", or your own
judgment. It must be an explicit yes from the citizen.

## Exit gate

`plan_approved == true`. `advance` prints `BLOCKED` until it is set. If blocked,
you have not gotten a clear yes — keep refining the plan.
