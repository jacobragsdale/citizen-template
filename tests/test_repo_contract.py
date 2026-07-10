import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]
SKILL_DIR = ROOT / ".agents/skills/citizen-app"
STATE_SCRIPT = SKILL_DIR / "scripts/state.py"


def load_state() -> ModuleType:
    spec = importlib.util.spec_from_file_location("citizen_state", STATE_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def relevant_text_files() -> list[Path]:
    ignored_roots = {".git", ".venv", ".pytest_cache", ".ruff_cache"}
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not any(part in ignored_roots for part in path.relative_to(ROOT).parts)
        and path.suffix in {".md", ".py", ".json", ".yaml", ".toml", ".template"}
    ]


def test_legacy_agent_paths_are_absent() -> None:
    legacy_paths = (".cl" + "aude", ".Co" + "dex")

    offenders = [
        str(path.relative_to(ROOT))
        for path in relevant_text_files()
        if any(legacy in path.read_text(errors="ignore") for legacy in legacy_paths)
    ]

    assert not (ROOT / legacy_paths[0]).exists()
    assert offenders == []


def test_every_active_stage_has_exactly_one_numbered_playbook() -> None:
    state = load_state()

    for number, stage in enumerate(state.STAGES[:-1], start=1):
        matches = list((SKILL_DIR / "stages").glob(f"{number:02d}-{stage}.md"))
        assert len(matches) == 1, f"{stage}: {matches}"


def test_citizen_handoff_never_calls_the_pull_request_live() -> None:
    citizen_docs = [
        ROOT / "README.md",
        SKILL_DIR / "SKILL.md",
        *sorted((SKILL_DIR / "stages").glob("*.md")),
    ]
    forbidden = ("app is live", "application is live", "job is scheduled")

    offenders = [
        str(path.relative_to(ROOT))
        for path in citizen_docs
        if any(phrase in path.read_text().lower() for phrase in forbidden)
    ]

    assert offenders == []
