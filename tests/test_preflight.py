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

    assert names == ["Python project tools", "Git", "Browser"]


def test_container_handoff_adds_an_early_docker_check() -> None:
    preflight = load_preflight()

    names = [check.name for check in preflight.planned_checks("github", True)]

    assert names == [
        "Python project tools",
        "Git",
        "Browser",
        "GitHub sign-in",
        "Container engine",
    ]


def test_external_container_handoff_does_not_require_a_local_daemon() -> None:
    preflight = load_preflight()

    names = [check.name for check in preflight.planned_checks("local", False)]

    assert names == ["Python project tools", "Git", "Browser"]


def test_capability_results_distinguish_browser_and_external_container() -> None:
    preflight = load_preflight()
    browser = preflight.browser_command()

    capabilities, details = preflight.assess_capabilities(
        "local",
        "external",
        exists=lambda command: command != browser,
        succeeds=lambda command, **_: True,
    )

    assert capabilities["repository_provider"] == "local_only"
    assert capabilities["container_engine"] == "externalized"
    assert capabilities["browser"] == "missing"
    browser = next(check for check, _ in details if check.key == "browser")
    assert browser.blocking is False


def test_container_engine_can_be_installed_but_not_ready() -> None:
    preflight = load_preflight()

    capabilities, _ = preflight.assess_capabilities(
        "github",
        "local",
        exists=lambda _: True,
        succeeds=lambda command, **_: command[0] != "docker",
    )

    assert capabilities["container_engine"] == "installed_not_ready"
