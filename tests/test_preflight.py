import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]
PREFLIGHT_SCRIPT = ROOT / ".agents/skills/citizen-app/scripts/preflight.py"


def load_preflight() -> ModuleType:
    spec = importlib.util.spec_from_file_location("citizen_preflight", PREFLIGHT_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_local_preflight_does_not_require_github_authentication() -> None:
    preflight = load_preflight()

    names = [check.name for check in preflight.planned_checks("local", False)]

    assert names == ["uv", "git"]


def test_container_handoff_adds_an_early_docker_check() -> None:
    preflight = load_preflight()

    names = [check.name for check in preflight.planned_checks("github", True)]

    assert names == ["uv", "git", "GitHub sign-in", "Docker"]
