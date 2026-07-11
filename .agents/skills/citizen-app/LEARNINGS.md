# Learnings

Dated corrections from real use of this skill. Read before executing; fold
recurring or user-confirmed entries into the relevant playbook and remove them
from here.

Format: `- YYYY-MM-DD: <what happened> → <what to do instead>`

- 2026-07-10: Three Windows runs failed on implicit cp1252 text reads/writes before run-local UTF-8 fixes passed → specify `encoding="utf-8"` at every workflow/test text boundary and add Windows coverage.
- 2026-07-10: Bash-only examples and positional JSON were unreliable through PowerShell/native `uv` argument handling → provide tested PowerShell or OS-neutral commands and accept structured state input from a file or stdin.
- 2026-07-10: `record-build` accepted a revision with known lint/type failures and can count bundled workflow tests as behavior evidence → require current build-check evidence and named application acceptance tests before preview.
- 2026-07-10: Dashboard preview evidence omitted important numeric/multiselect controls and metrics, while the container gate did not execute the built image → make preview evidence acceptance-aware and require a type-specific container runtime smoke check.
- 2026-07-10: Docker Desktop presence/status did not prove engine readiness, and its credential helper could not pull public images from an SSH logon → preflight must poll `docker info` and explain Windows interactive-session credential limits.
- 2026-07-10: Windows PowerShell 5.1 blocked staged scripts and decoded UTF-8-without-BOM script literals as the legacy ANSI code page → use process-scoped execution-policy bypass and add a UTF-8 BOM only to generated PowerShell scripts containing non-ASCII values.
- 2026-07-10: A demoted Windows account was denied CIM/WMI inventory although normal development commands worked → read OS identity from the standard-user-readable registry and physical memory through the .NET `ComputerInfo` API.
- 2026-07-11: Harmless uv stderr warnings were merged into successful job preview output and broke exact approval evidence → keep application stdout as the approval artifact and write stderr to a sibling diagnostic file.
- 2026-07-11: Project fingerprints included `__pycache__` bytecode, so a passing pytest run made preview approval stale → exclude generated cache directories and bytecode from source identity.
- 2026-07-11: Cross-platform lock resolution on macOS omitted Windows-only transitive packages needed by Streamlit → seed the staged Windows wheelhouse with explicit platform packages and verify installation in the disposable guest.
- 2026-07-11: A lock generated for the controller checkout retained a machine-local editable source and could not verify the staged Windows workspace → resolve and lock the generated application as its own portable project before transfer.
- 2026-07-11: A detached Streamlit process inherited an SSH session lifetime and exited when the controller disconnected → keep the controller transport alive for browser review, then stop the registered VM during cleanup.
