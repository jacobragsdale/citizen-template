# Stage 01 — scaffold

Goal: create or adopt a safe working repository and discover missing tools
before the citizen invests time in the interview.

## First conversation

Ask what they would like to call the app and what they hope it will help with.
Create a lowercase hyphenated name prefixed with `citizen-`, show it, and wait
for confirmation.

Then ask where the draft should live:

- **Private GitHub repository** — the currently implemented publishing path.
- **Only on this computer for now** — safe for trying the workflow, but the
  ship stage will wait for an internal repository integration.

Never create a public repository unless the citizen explicitly requests and
confirms it after you explain that its code and plan will be internet-visible.

## Preflight

Run this before creating anything, with `local` or `github` to match the answer:

```bash
uv run .agents/skills/citizen-app/scripts/preflight.py --provider github --require-container
```

For a standard-user Windows rehearsal whose image will be built by the
fingerprinted external verifier:

```powershell
uv run .agents/skills/citizen-app/scripts/preflight.py --provider local --container-mode external
```

Translate any failure. Core tools and, for GitHub, authentication are immediate
blockers. Docker is checked now when the image will be built locally; external
verification records the same runtime evidence without requiring Docker in the
guest.

## Detect template versus application

```bash
git remote get-url origin 2>/dev/null
```

If `.plan/state.json` exists or the repository name already begins with
`citizen-`, use the Adopt path. Otherwise use Create.

## Create

### Private GitHub repository

Do not assume the template and destination have the same owner. Discover the
current template repository and authenticated destination owner:

```bash
TEMPLATE=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
OWNER=$(gh api user --jq .login)
DEST="$OWNER/citizen-<slug>"
gh repo create "$DEST" --template "$TEMPLATE" --private
```

Template population can lag behind repository creation. Poll for a known file
before cloning, then verify the clone instead of accepting an empty directory:

```bash
for attempt in 1 2 3 4 5; do
  gh api "repos/$DEST/contents/pyproject.toml" >/dev/null 2>&1 && break
  sleep 2
done
git clone "https://github.com/$DEST.git" "../citizen-<slug>"
test -f "../citizen-<slug>/pyproject.toml"
```

If the final check fails, fetch and check out the populated default branch in
the new clone. Do not continue with an empty working copy.

### Local draft

```bash
git clone --no-hardlinks "$PWD" "../citizen-<slug>"
git -C "../citizen-<slug>" remote remove origin
```

Run every remaining command from the new sibling folder.

## Adopt and record

From the application repository:

```bash
uv run .agents/skills/citizen-app/scripts/state.py init --name "$(basename "$PWD")"
uv run .agents/skills/citizen-app/scripts/state.py set repo_provider github
uv run .agents/skills/citizen-app/scripts/state.py set repo_visibility private
uv run .agents/skills/citizen-app/scripts/state.py set repo_url "$(git remote get-url origin)"
uv run .agents/skills/citizen-app/scripts/state.py set workspace_ready true
uv run .agents/skills/citizen-app/scripts/state.py advance
```

For a local draft, set provider and visibility to `local` and omit `repo_url`.

Enterprise GitHub and Azure DevOps creation remain blocked until the provider
contract in `CORPORATE_INTEGRATION.md` is completed. Do not guess internal
commands or silently substitute a public repository.
