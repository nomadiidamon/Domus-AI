"""Check and install Domus dependencies using Hestia's software tooling."""

from __future__ import annotations

import importlib.util
import platform
import subprocess
import sys
from pathlib import Path

from Hestia.software.dependency import DependencyKind
from Hestia.software.installer import (
    InstallActionStatus, InstallAuthorization, InstallOutcome, InstallRequest, Installer,
)

if __package__:
    from .requirements import build_registry as _build_checker
else:
    _spec = importlib.util.spec_from_file_location("domus_requirements", Path(__file__).with_name("requirements.py"))
    _requirements = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_requirements)
    _build_checker = _requirements.build_registry

INSTALL_URLS = {
    "ollama": "https://ollama.com/download",
    "git": "https://git-scm.com/downloads",
    "claude": "https://github.com/anthropics/claude-code",
    "python": "https://www.python.org/downloads/",
}


class PipBackend:
    def install(self, request, *, timeout_seconds, report_progress):
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", request.target],
                capture_output=True, text=True, timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise TimeoutError("pip installation timed out") from error
        if result.returncode:
            return InstallOutcome(False, result.stderr or result.stdout or "pip installation failed")
        return InstallOutcome(True, f"Installed {request.target}")


def check_and_repair(auto_repair: bool = True) -> tuple[bool, dict]:
    """Check configured dependencies and optionally install Python packages."""
    registry = _build_checker()
    print("\n[CHECK] Checking dependencies...")
    print("-" * 50)
    results = registry.check_all()
    _print_check_results(results)
    failed_actions = set()

    if auto_repair:
        requests = [
            InstallRequest(
                action_id=f"install-{name}", group_id="domus-runtime",
                dependency_name=name, backend="pip",
                target=f"{name}{result.version_specifier or ''}",
            )
            for name, result in results.items()
            if result.kind == DependencyKind.PYTHON_PACKAGE
        ]
        if requests:
            installer = Installer(registry, {"pip": PipBackend()})
            plan = installer.plan(requests, results)
            if plan.actions:
                print("\n[REPAIR] Installing missing Python packages...")
                authorization = InstallAuthorization(plan.group_id, frozenset(action.action_id for action in plan.actions))
                report = installer.execute(plan, authorization)
                for action in report.actions:
                    success = action.status == InstallActionStatus.SUCCEEDED
                    print(f"  {'[OK]' if success else '[X]'} {action.dependency_name}: {action.message}")
                    if not success:
                        failed_actions.add(action.dependency_name)
                results.update(report.rechecks)
                print("\n[RECHECK] Re-checking after repair...")
                _print_check_results(results)

    all_required_ok = all(
        not result.required or (result.is_satisfied and name not in failed_actions)
        for name, result in results.items()
    )
    return all_required_ok, results


def _print_check_results(results: dict) -> None:
    for name, result in results.items():
        if result.is_satisfied:
            version = f"  ({result.version})" if result.version else ""
            print(f"  [OK] {name}{version}")
        else:
            marker = "[X]" if result.required else "[!]"
            print(f"  {marker} {name}: {result.message}")
            if result.kind == DependencyKind.PYTHON_PACKAGE:
                print(f'     -> python -m pip install --upgrade "{name}{result.version_specifier or ""}"')
            else:
                print(f"     -> Install {name} and ensure it is on PATH")
                if name in INSTALL_URLS:
                    print(f"     -> {INSTALL_URLS[name]}")


def run_install(auto_repair: bool = True) -> bool:
    print("\n" + "=" * 50)
    print("[INSTALL] Local AI Runtime - Installer")
    print("=" * 50)
    print(f"Python:   {sys.version.split()[0]}")
    print(f"Platform: {platform.system()} {platform.release()}")
    all_ok, _ = check_and_repair(auto_repair=auto_repair)
    print("\n" + "=" * 50)
    print("[SUMMARY] Installation Summary")
    print("=" * 50)
    if all_ok:
        print("[OK] All required dependencies are satisfied.")
        print("  Run: python -m Janus help")
    else:
        print("[X] Some required dependencies are not satisfied.")
        print("  Follow the instructions above, then re-run python install.py")
    return all_ok