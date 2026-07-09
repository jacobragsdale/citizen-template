# Stage 07 — preview (see it before shipping)

Goal: let the citizen actually see the finished app before it goes to GitHub.
This is a gate — do not ship until they've looked and are happy.

## If `app_type == "ui"`

1. Tell the citizen you're going to open the app so they can try it, then start
   it in the background (do not block the session):
   ```bash
   uv run --env-file .env streamlit run src/app/ui.py --server.address 127.0.0.1 --server.port 8501
   ```
   Run this in the background so you can keep talking to them. If port 8501 is
   already in use, pick another free port and use it in both the command and the
   link below.
2. Give them the link in plain language: "Your app is running — open
   **http://localhost:8501** in your browser to try it out." Wait for them.
3. Ask what they think:
   - **Changes wanted?** Set `validation.passed` back to `false`, go back to the
     build stage, make the changes, re-validate, and return here. (Never ship an
     app they haven't approved.)
   - **Happy?** Stop the running app (terminate the background process) and go to
     step 4.
4. Record it and advance:
   ```bash
   uv run .claude/skills/citizen-app/scripts/state.py set previewed true
   uv run .claude/skills/citizen-app/scripts/state.py advance
   ```

## If `app_type == "job"`

Jobs have no screen, so show them what it produces instead:

1. Run it in **dry-run** mode, which exercises the real wiring and prints what it
   would do without firing any side effect (sending a message, writing a file):
   ```bash
   uv run --env-file .env python -m app.job --dry-run
   ```
   Only do a real run (drop `--dry-run`) if the citizen explicitly asks to see a
   live one and understands it will actually act (e.g. post to their chat).
2. Explain the output plainly and ask if it's what they expected. Handle changes
   vs. happy exactly as in the UI case (loop back to build, or approve).
3. Record and advance:
   ```bash
   uv run .claude/skills/citizen-app/scripts/state.py set previewed true
   uv run .claude/skills/citizen-app/scripts/state.py advance
   ```

## Exit gate

`previewed == true`. `advance` prints `BLOCKED` until it's set — and only set it
after the citizen has actually seen the app and said they're happy.
