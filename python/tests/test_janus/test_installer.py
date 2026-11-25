"""Tests for the Hestia-backed Domus installer."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from Hestia.software.dependency import (
    CheckResult, Dependency, DependencyKind, DependencyRegistry, DependencyStatus,
)
from Hestia.software.installer import InstallOutcome

from Janus import installer

pytestmark = pytest.mark.janus


def make_registry(state, required=True, kind=DependencyKind.PYTHON_PACKAGE):
    registry = DependencyRegistry()
    registry.register(Dependency(
        "example", lambda: CheckResult(state["status"], "example status", version="1.0"),
        kind, required, ">=1.0" if kind == DependencyKind.PYTHON_PACKAGE else None,
    ))
    return registry


def test_shared_registry_contains_runtime_requirements():
    results = installer._build_checker().check_all()
    assert set(results) == {
        "platformdirs", "auctor-utils", "python-dotenv", "nvidia-ml-py", "mercurius-events", "hestia-system",
        "python", "ollama", "git", "claude",
    }
    assert results["hestia-system"].version_specifier == ">=0.5.0"
    assert not results["claude"].required
    assert not results["nvidia-ml-py"].required
    assert results["platformdirs"].required
    assert results["auctor-utils"].required


@pytest.mark.parametrize("version, expected", [
    ("Python 3.10.0", DependencyStatus.SATISFIED),
    ("Python 3.9.9", DependencyStatus.INCOMPATIBLE),
])
def test_python_command_version_is_checked(version, expected):
    with patch("Hestia.software.dependency.checks.shutil.which", return_value="/python"), \
         patch("Hestia.software.dependency.checks.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = version
        run.return_value.stderr = ""
        result = installer._build_checker().check("python")
    assert result.status == expected
    assert run.call_args.args[0] == ["/python", "--version"]


@pytest.mark.parametrize("command, output, version", [
    ("ollama", "ollama version is 0.12.3", "0.12.3"),
    ("git", "git version 2.49.0", "2.49.0"),
])
def test_system_command_version_is_reported(command, output, version):
    with patch("Hestia.software.dependency.checks.shutil.which", return_value=f"/{command}"), \
         patch("Hestia.software.dependency.checks.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = output
        run.return_value.stderr = ""
        result = installer._build_checker().check(command)
    assert result.status == DependencyStatus.SATISFIED
    assert result.version == version
    assert run.call_args.args[0] == [f"/{command}", "--version"]


def test_check_only_does_not_run_backend():
    registry = make_registry({"status": DependencyStatus.MISSING})
    with patch.object(installer, "_build_checker", return_value=registry), \
         patch.object(installer.PipBackend, "install") as install:
        success, results = installer.check_and_repair(auto_repair=False)
    assert not success
    assert not results["example"].is_satisfied
    install.assert_not_called()


def test_repair_uses_hestia_plan_and_rechecks():
    state = {"status": DependencyStatus.MISSING}
    registry = make_registry(state)

    def install(request, *, timeout_seconds, report_progress):
        assert request.target == "example>=1.0"
        assert timeout_seconds > 0
        state["status"] = DependencyStatus.SATISFIED
        return InstallOutcome(True, "installed")

    with patch.object(installer, "_build_checker", return_value=registry), \
         patch.object(installer.PipBackend, "install", side_effect=install) as backend:
        success, results = installer.check_and_repair()
    assert success
    assert results["example"].is_satisfied
    backend.assert_called_once()


def test_failed_action_is_not_hidden_by_successful_recheck():
    state = {"status": DependencyStatus.MISSING}
    registry = make_registry(state)

    def install(request, *, timeout_seconds, report_progress):
        state["status"] = DependencyStatus.SATISFIED
        return InstallOutcome(False, "failed")

    with patch.object(installer, "_build_checker", return_value=registry), \
         patch.object(installer.PipBackend, "install", side_effect=install):
        success, results = installer.check_and_repair()
    assert not success
    assert results["example"].is_satisfied


def test_missing_optional_command_does_not_trigger_install_or_fail():
    registry = make_registry({"status": DependencyStatus.MISSING}, required=False, kind=DependencyKind.SYSTEM_COMMAND)
    with patch.object(installer, "_build_checker", return_value=registry), \
         patch.object(installer.PipBackend, "install") as install:
        success, _ = installer.check_and_repair()
    assert success
    install.assert_not_called()


def test_missing_optional_package_does_not_trigger_install_or_fail():
    registry = make_registry({"status": DependencyStatus.MISSING}, required=False)
    with patch.object(installer, "_build_checker", return_value=registry), \
         patch.object(installer.PipBackend, "install") as install:
        success, _ = installer.check_and_repair()
    assert success
    install.assert_not_called()


def test_missing_required_command_fails_without_installing():
    registry = make_registry({"status": DependencyStatus.MISSING}, kind=DependencyKind.SYSTEM_COMMAND)
    with patch.object(installer, "_build_checker", return_value=registry), \
         patch.object(installer.PipBackend, "install") as install:
        success, _ = installer.check_and_repair()
    assert not success
    install.assert_not_called()


def test_pip_backend_uses_interpreter_and_timeout():
    request = installer.InstallRequest("id", "group", "example", "pip", "example>=1")
    with patch.object(installer.subprocess, "run") as run:
        run.return_value.returncode = 0
        outcome = installer.PipBackend().install(request, timeout_seconds=4, report_progress=lambda *_: None)
    assert outcome.succeeded
    run.assert_called_once_with(
        [installer.sys.executable, "-m", "pip", "install", "--upgrade", "example>=1"],
        capture_output=True, text=True, timeout=4,
    )


def test_pip_timeout_is_reported_by_hestia():
    registry = make_registry({"status": DependencyStatus.MISSING})
    with patch.object(installer, "_build_checker", return_value=registry), \
         patch.object(installer.subprocess, "run", side_effect=subprocess.TimeoutExpired("pip", 4)):
        success, results = installer.check_and_repair()
    assert not success
    assert not results["example"].is_satisfied


def test_standalone_installer_explains_missing_hestia():
    script = Path(__file__).resolve().parents[2] / "install.py"
    result = subprocess.run(
        [sys.executable, "-S", str(script), "--check-only"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    assert 'python -m pip install "hestia-system>=0.5.0"' in result.stderr


def test_run_install_passes_repair_flag():
    with patch.object(installer, "check_and_repair", return_value=(True, {})) as check:
        assert installer.run_install(auto_repair=False)
    check.assert_called_once_with(auto_repair=False)