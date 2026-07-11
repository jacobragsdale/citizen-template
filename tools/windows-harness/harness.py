"""Orchestrate a disposable no-admin Windows run through the VM adapter."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from collect import collect
from prepare import prepare_payload

HARNESS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HARNESS_DIR.parents[1]
DEFAULT_ADAPTER = Path.home() / "Development/home-server/scripts/vm-test.sh"
DASHBOARD_SCENARIOS = {"dashboard-happy", "encoding-paths", "revision-stress"}


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command), flush=True)
    result = subprocess.run(command, cwd=cwd, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"command failed with exit code {result.returncode}: {command}")
    return result


def adapter(adapter_path: Path, *arguments: str) -> None:
    run([str(adapter_path), *arguments])


def powershell_path(*parts: str) -> str:
    return "C:\\" + "\\".join(parts)


def start_dashboard_preview(
    adapter_path: Path, run_id: str
) -> tuple[dict[str, object], subprocess.Popen[bytes]]:
    run_root = powershell_path(
        "Users", "jacob", "AppData", "Local", "CitizenHarness", "runs", run_id
    )
    workspace = run_root + "\\Citizen Apps\\café demo"
    preview_dir = run_root + "\\evidence\\preview"
    command = (
        "Set-ExecutionPolicy -Scope Process Bypass -Force; "
        f". '{run_root}\\environment.ps1'; "
        f"New-Item -ItemType Directory -Force '{preview_dir}' | Out-Null; "
        f"Set-Location '{workspace}'; "
        "uv run streamlit run src/app/ui.py --server.address 0.0.0.0 "
        "--server.port 8501 --server.headless true "
        f"*> '{preview_dir}\\streamlit.combined.txt'"
    )
    process = subprocess.Popen(
        [str(adapter_path), "exec", "--run-id", run_id, "--", command],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    health_url = "http://100.103.224.99:8501/_stcore/health"
    last_error = "preview did not answer"
    for _ in range(30):
        if process.poll() is not None:
            raise RuntimeError(f"dashboard SSH process exited early with code {process.returncode}")
        try:
            with urllib.request.urlopen(health_url, timeout=3) as response:
                body = response.read().decode("utf-8", errors="replace")
                if response.status == 200 and "ok" in body.lower():
                    return (
                        {
                            "schema_version": 1,
                            "url": health_url,
                            "status": response.status,
                            "body": body,
                        },
                        process,
                    )
        except OSError as exc:
            last_error = str(exc)
        time.sleep(2)
    raise RuntimeError(f"dashboard was not reachable from the controller: {last_error}")


def external_container_verification(run_dir: Path, run_id: str, adapter_path: Path) -> Path:
    evidence = run_dir / "evidence"
    source = evidence / "source.zip"
    if not source.is_file():
        raise RuntimeError("scenario did not return a source archive for container verification")
    builder = run_dir / "builder"
    builder.mkdir()
    with zipfile.ZipFile(source) as archive:
        archive.extractall(builder)
    container_script = builder / ".agents/skills/citizen-app/scripts/container.py"
    run(
        [
            sys.executable,
            str(container_script),
            "--tag",
            f"citizen-harness-{run_id}:local",
            "--no-record",
        ],
        cwd=builder,
    )
    container_evidence = builder / ".plan/container/verification.json"
    if not container_evidence.is_file():
        raise RuntimeError("external container verifier did not write evidence")

    guest_container_dir = powershell_path(
        "Users",
        "jacob",
        "AppData",
        "Local",
        "CitizenHarness",
        "runs",
        run_id,
        "Citizen Apps",
        "café demo",
        ".plan",
        "container",
    )
    adapter(
        adapter_path,
        "exec",
        "--run-id",
        run_id,
        "--",
        f"New-Item -ItemType Directory -Force '{guest_container_dir}' | Out-Null",
    )
    adapter(
        adapter_path,
        "copy-in",
        "--run-id",
        run_id,
        str(container_evidence),
        guest_container_dir + "\\verification.json",
    )
    guest_run_root = powershell_path(
        "Users", "jacob", "AppData", "Local", "CitizenHarness", "runs", run_id
    )
    guest_workspace = guest_run_root + "\\Citizen Apps\\café demo"
    record_command = (
        "Set-ExecutionPolicy -Scope Process Bypass -Force; "
        f". '{guest_run_root}\\environment.ps1'; "
        f"Set-Location '{guest_workspace}'; "
        "uv run .agents/skills/citizen-app/scripts/state.py "
        "record-container-verification --evidence .plan/container/verification.json; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        "uv run .agents/skills/citizen-app/scripts/state.py advance"
    )
    adapter(adapter_path, "exec", "--run-id", run_id, "--", record_command)
    return container_evidence


def run_scenario(args: argparse.Namespace) -> None:
    os.environ["HARNESS_RAM_SIZE"] = args.memory
    adapter_path = args.adapter.resolve()
    if not adapter_path.is_file():
        raise FileNotFoundError(f"VM adapter is missing: {adapter_path}")
    run_dir = (REPO_ROOT / ".test-runs" / args.run_id).resolve()
    if run_dir.exists():
        raise FileExistsError(f"run evidence already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    payload_dir = run_dir / "payload"
    prepare_payload(
        payload_dir,
        args.cache_dir.resolve(),
        include_wheelhouse=not args.skip_wheelhouse,
    )
    created = False
    preview_process: subprocess.Popen[bytes] | None = None
    try:
        adapter(adapter_path, "create", "--run-id", args.run_id)
        created = True
        guest_payload = powershell_path("Users", "jacob", "CitizenHarnessPayload", args.run_id)
        adapter(
            adapter_path,
            "exec",
            "--run-id",
            args.run_id,
            "--",
            f"New-Item -ItemType Directory -Force '{guest_payload}' | Out-Null",
        )
        adapter(
            adapter_path,
            "copy-in",
            "--run-id",
            args.run_id,
            str(payload_dir) + os.sep,
            guest_payload,
        )
        adapter(
            adapter_path,
            "exec",
            "--run-id",
            args.run_id,
            "--",
            (
                "Set-ExecutionPolicy -Scope Process Bypass -Force; "
                f"& '{guest_payload}\\bootstrap.ps1' "
                f"-RunId '{args.run_id}' -PayloadDir '{guest_payload}'"
            ),
        )
        adapter(
            adapter_path,
            "exec",
            "--run-id",
            args.run_id,
            "--",
            (
                "Set-ExecutionPolicy -Scope Process Bypass -Force; "
                f"& '{guest_payload}\\run-scenario.ps1' "
                f"-RunId '{args.run_id}' -Scenario '{args.scenario}'"
            ),
        )
        local_evidence = run_dir / "evidence"
        controller_health: dict[str, object] | None = None
        if args.scenario in DASHBOARD_SCENARIOS:
            controller_health, preview_process = start_dashboard_preview(adapter_path, args.run_id)
        guest_evidence = powershell_path(
            "Users",
            "jacob",
            "AppData",
            "Local",
            "CitizenHarness",
            "runs",
            args.run_id,
            "evidence",
        )
        adapter(
            adapter_path,
            "copy-out",
            "--run-id",
            args.run_id,
            guest_evidence,
            str(local_evidence),
        )
        if controller_health is not None:
            preview_evidence = local_evidence / "preview"
            preview_evidence.mkdir(parents=True, exist_ok=True)
            (preview_evidence / "controller-health.json").write_text(
                json.dumps(controller_health, indent=2) + "\n",
                encoding="utf-8",
            )
        result = collect(local_evidence)
        if result["source_archive"]:
            container_evidence = external_container_verification(run_dir, args.run_id, adapter_path)
            shutil.copy2(container_evidence, local_evidence / "container-verification.json")
            final_state = local_evidence / "final-state.json"
            guest_final_state = powershell_path(
                "Users",
                "jacob",
                "AppData",
                "Local",
                "CitizenHarness",
                "runs",
                args.run_id,
                "Citizen Apps",
                "café demo",
                ".plan",
                "state.json",
            )
            adapter(
                adapter_path,
                "copy-out",
                "--run-id",
                args.run_id,
                guest_final_state,
                str(final_state),
            )
            state_payload = json.loads(final_state.read_text(encoding="utf-8"))
            result["stage"] = state_payload.get("stage")
            result["container_verified"] = True
        (run_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if not args.keep_running:
            adapter(adapter_path, "stop", "--run-id", args.run_id)
            if preview_process is not None:
                preview_process.wait(timeout=30)
            if not args.keep_run_disk:
                adapter(adapter_path, "destroy-run", "--run-id", args.run_id, "--yes")
        else:
            print("Run remains active for controller-owned browser review.")
        print(run_dir / "result.json")
    except Exception:
        if created:
            subprocess.run([str(adapter_path), "stop", "--run-id", args.run_id], check=False)
            if preview_process is not None:
                try:
                    preview_process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    preview_process.terminate()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="prepare a staged payload")
    prepare_parser.add_argument("--output", type=Path, required=True)
    prepare_parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache/citizen-windows-harness",
    )
    prepare_parser.add_argument("--skip-wheelhouse", action="store_true")

    run_parser = subparsers.add_parser("run", help="run one disposable Windows scenario")
    run_parser.add_argument("--run-id", required=True)
    run_parser.add_argument(
        "--scenario",
        required=True,
        choices=(
            "bootstrap-smoke",
            "dashboard-happy",
            "job-happy",
            "revision-stress",
            "encoding-paths",
            "resume",
            "network-denied",
            "missing-browser",
        ),
    )
    run_parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    run_parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache/citizen-windows-harness",
    )
    run_parser.add_argument("--skip-wheelhouse", action="store_true")
    run_parser.add_argument("--keep-run-disk", action="store_true")
    run_parser.add_argument(
        "--keep-running",
        action="store_true",
        help="leave the guest and preview running for controller-owned browser review",
    )
    run_parser.add_argument(
        "--memory",
        choices=("8G", "4G"),
        default="8G",
        help="guest RAM; 8G is the golden path and 4G is the constrained profile",
    )

    args = parser.parse_args()
    if args.command == "prepare":
        manifest = prepare_payload(
            args.output.resolve(),
            args.cache_dir.resolve(),
            include_wheelhouse=not args.skip_wheelhouse,
        )
        print(manifest)
    else:
        run_scenario(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
