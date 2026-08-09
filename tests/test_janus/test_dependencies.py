"""
Tests for Janus/dependencies.py

Every dependency check either imports a real package, shells out via
subprocess, touches the filesystem, or reads os.environ. To keep this
suite hermetic and fast:
  - PythonPackageDependency is tested against `os` (a real stdlib module
    guaranteed to be importable everywhere) for the "present" path, and
    a name that can't possibly exist for the "missing" path — no mocking
    needed since we're not asserting anything about *our* project's deps.
  - SystemCommandDependency mocks subprocess.run.
  - DirectoryDependency and EnvironmentVariableDependency use tmp_path /
    monkeypatch respectively — both are naturally hermetic already.
  - DependencyChecker is tested against small fake Dependency subclasses
    defined locally, so its aggregation logic is tested independently of
    any real dependency's check()/repair() behavior.
"""

from unittest.mock import patch, MagicMock

import pytest

from Janus.dependencies import (
    DependencyStatus,
    DependencyType,
    DependencyCheckResult,
    Dependency,
    PythonPackageDependency,
    SystemCommandDependency,
    DirectoryDependency,
    EnvironmentVariableDependency,
    DependencyChecker,
)

pytestmark = pytest.mark.janus


# ---------------------------------------------------------------------------
# DependencyCheckResult
# ---------------------------------------------------------------------------
class TestDependencyCheckResult:
    def test_is_healthy_true_for_healthy_and_degraded(self):
        for status in (DependencyStatus.HEALTHY, DependencyStatus.DEGRADED):
            result = DependencyCheckResult(name="x", dep_type=DependencyType.PYTHON_PACKAGE, status=status)
            assert result.is_healthy is True

    def test_is_healthy_false_for_missing_broken_incompatible(self):
        for status in (DependencyStatus.MISSING, DependencyStatus.BROKEN, DependencyStatus.INCOMPATIBLE):
            result = DependencyCheckResult(name="x", dep_type=DependencyType.PYTHON_PACKAGE, status=status)
            assert result.is_healthy is False

    def test_is_critical_true_for_missing_and_broken(self):
        for status in (DependencyStatus.MISSING, DependencyStatus.BROKEN):
            result = DependencyCheckResult(name="x", dep_type=DependencyType.PYTHON_PACKAGE, status=status)
            assert result.is_critical is True

    def test_is_critical_false_for_healthy(self):
        result = DependencyCheckResult(name="x", dep_type=DependencyType.PYTHON_PACKAGE, status=DependencyStatus.HEALTHY)
        assert result.is_critical is False

    def test_to_dict_converts_enums_to_strings(self):
        result = DependencyCheckResult(
            name="x", dep_type=DependencyType.SYSTEM_COMMAND, status=DependencyStatus.HEALTHY,
        )
        data = result.to_dict()
        assert data["dep_type"] == "system_command"
        assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# PythonPackageDependency
# ---------------------------------------------------------------------------
class TestPythonPackageDependency:
    def test_check_healthy_for_installed_package(self):
        dep = PythonPackageDependency("os")  # stdlib, always importable
        result = dep.check()
        assert result.status == DependencyStatus.HEALTHY

    def test_check_missing_for_nonexistent_package(self):
        dep = PythonPackageDependency("this_package_definitely_does_not_exist_xyz")
        result = dep.check()
        assert result.status == DependencyStatus.MISSING

    def test_check_uses_import_name_when_different_from_package_name(self):
        dep = PythonPackageDependency(package_name="totally-fake-pip-name", import_name="os")
        result = dep.check()
        assert result.status == DependencyStatus.HEALTHY

    def test_get_install_instructions_with_min_version(self):
        dep = PythonPackageDependency("somepkg", min_version="2.0")
        assert dep.get_install_instructions() == "pip install 'somepkg>=2.0'"

    def test_get_install_instructions_without_version(self):
        dep = PythonPackageDependency("somepkg")
        assert dep.get_install_instructions() == "pip install somepkg"

    def test_repair_calls_pip_install_with_expected_command(self):
        dep = PythonPackageDependency("somepkg", min_version="1.5")
        fake_result = MagicMock(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", return_value=fake_result) as mock_run:
            success, message = dep.repair()

        assert success is True
        args = mock_run.call_args[0][0]
        assert args[-1] == "somepkg>=1.5"
        assert "pip" in args

    def test_repair_reports_failure_on_nonzero_exit(self):
        dep = PythonPackageDependency("somepkg")
        fake_result = MagicMock(returncode=1, stdout="", stderr="permission denied")

        with patch("subprocess.run", return_value=fake_result):
            success, message = dep.repair()

        assert success is False
        assert "permission denied" in message

    def test_repair_handles_timeout(self):
        import subprocess as sp
        dep = PythonPackageDependency("somepkg")

        with patch("subprocess.run", side_effect=sp.TimeoutExpired(cmd="pip", timeout=300)):
            success, message = dep.repair()

        assert success is False
        assert "timeout" in message.lower()


# ---------------------------------------------------------------------------
# SystemCommandDependency
# ---------------------------------------------------------------------------
class TestSystemCommandDependency:
    def test_check_healthy_when_command_succeeds(self):
        dep = SystemCommandDependency("git")
        fake_result = MagicMock(returncode=0, stdout="git version 2.40.0\n")

        with patch("subprocess.run", return_value=fake_result):
            result = dep.check()

        assert result.status == DependencyStatus.HEALTHY
        assert result.version == "git version 2.40.0"

    def test_check_degraded_on_nonzero_exit(self):
        dep = SystemCommandDependency("somecmd")
        fake_result = MagicMock(returncode=1, stdout="")

        with patch("subprocess.run", return_value=fake_result):
            result = dep.check()

        assert result.status == DependencyStatus.DEGRADED

    def test_check_missing_when_not_found(self):
        dep = SystemCommandDependency("somecmd")
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = dep.check()
        assert result.status == DependencyStatus.MISSING

    def test_check_broken_on_timeout(self):
        import subprocess as sp
        dep = SystemCommandDependency("somecmd")
        with patch("subprocess.run", side_effect=sp.TimeoutExpired(cmd="somecmd", timeout=5)):
            result = dep.check()
        assert result.status == DependencyStatus.BROKEN

    @pytest.mark.parametrize(
        "system,expected_snippet",
        [
            ("Linux", "apt-get install"),
            ("Darwin", "brew install"),
            ("Windows", "Download and install"),
        ],
    )
    def test_get_install_instructions_per_platform(self, system, expected_snippet):
        dep = SystemCommandDependency("git")
        with patch("platform.system", return_value=system):
            instructions = dep.get_install_instructions()
        assert expected_snippet in instructions

    def test_repair_windows_not_supported(self):
        dep = SystemCommandDependency("git")
        with patch("platform.system", return_value="Windows"):
            success, message = dep.repair()
        assert success is False
        assert "not supported" in message.lower()

    def test_repair_linux_tries_apt_then_yum(self):
        dep = SystemCommandDependency("git")
        apt_fail = MagicMock(returncode=1)
        yum_ok = MagicMock(returncode=0)

        with patch("platform.system", return_value="Linux"), \
             patch("subprocess.run", side_effect=[apt_fail, yum_ok]) as mock_run:
            success, message = dep.repair()

        assert success is True
        assert mock_run.call_count == 2
        assert "yum" in message


# ---------------------------------------------------------------------------
# DirectoryDependency
# ---------------------------------------------------------------------------
class TestDirectoryDependency:
    def test_check_healthy_when_directory_exists(self, tmp_path):
        dep = DirectoryDependency(tmp_path)
        result = dep.check()
        assert result.status == DependencyStatus.HEALTHY

    def test_check_missing_when_directory_absent(self, tmp_path):
        dep = DirectoryDependency(tmp_path / "does_not_exist")
        result = dep.check()
        assert result.status == DependencyStatus.MISSING

    def test_repair_creates_directory(self, tmp_path):
        target = tmp_path / "new_dir" / "nested"
        dep = DirectoryDependency(target)

        success, message = dep.repair()

        assert success is True
        assert target.exists()

    def test_repair_disabled_when_create_if_missing_false(self, tmp_path):
        target = tmp_path / "should_not_be_created"
        dep = DirectoryDependency(target, create_if_missing=False)

        success, message = dep.repair()

        assert success is False
        assert not target.exists()

    def test_get_install_instructions(self, tmp_path):
        dep = DirectoryDependency(tmp_path / "x")
        assert "mkdir -p" in dep.get_install_instructions()


# ---------------------------------------------------------------------------
# EnvironmentVariableDependency
# ---------------------------------------------------------------------------
class TestEnvironmentVariableDependency:
    def test_check_missing_when_unset(self, monkeypatch):
        monkeypatch.delenv("TEST_DOMUS_ENVDEP", raising=False)
        dep = EnvironmentVariableDependency("TEST_DOMUS_ENVDEP")
        result = dep.check()
        assert result.status == DependencyStatus.MISSING

    def test_check_healthy_when_set(self, monkeypatch):
        monkeypatch.setenv("TEST_DOMUS_ENVDEP", "anything")
        dep = EnvironmentVariableDependency("TEST_DOMUS_ENVDEP")
        result = dep.check()
        assert result.status == DependencyStatus.HEALTHY

    def test_check_degraded_when_value_does_not_match_expected(self, monkeypatch):
        monkeypatch.setenv("TEST_DOMUS_ENVDEP", "wrong")
        dep = EnvironmentVariableDependency("TEST_DOMUS_ENVDEP", expected_value="right")
        result = dep.check()
        assert result.status == DependencyStatus.DEGRADED

    def test_repair_always_fails(self, monkeypatch):
        monkeypatch.setenv("TEST_DOMUS_ENVDEP", "x")
        dep = EnvironmentVariableDependency("TEST_DOMUS_ENVDEP")
        success, message = dep.repair()
        assert success is False


# ---------------------------------------------------------------------------
# DependencyChecker
# ---------------------------------------------------------------------------
class _FakeDependency(Dependency):
    """Minimal concrete Dependency for exercising DependencyChecker in isolation."""

    def __init__(self, name, status=DependencyStatus.HEALTHY, required=True, raise_on_check=False):
        super().__init__(name=name, dep_type=DependencyType.PYTHON_PACKAGE, required=required)
        self._status = status
        self._raise_on_check = raise_on_check
        self.repair_called = False

    def check(self):
        if self._raise_on_check:
            raise RuntimeError("check exploded")
        return DependencyCheckResult(name=self.name, dep_type=self.dep_type, status=self._status)

    def repair(self):
        self.repair_called = True
        return True, "repaired"


class TestDependencyChecker:
    def test_register_and_check_all(self):
        checker = DependencyChecker()
        checker.register(_FakeDependency("a", DependencyStatus.HEALTHY))
        checker.register(_FakeDependency("b", DependencyStatus.MISSING))

        results = checker.check_all()

        assert set(results.keys()) == {"a", "b"}
        assert results["a"].status == DependencyStatus.HEALTHY
        assert results["b"].status == DependencyStatus.MISSING

    def test_register_many(self):
        checker = DependencyChecker()
        checker.register_many([_FakeDependency("a"), _FakeDependency("b")])
        assert set(checker.dependencies.keys()) == {"a", "b"}

    def test_check_all_skip_optional(self):
        checker = DependencyChecker()
        checker.register(_FakeDependency("required", required=True))
        checker.register(_FakeDependency("optional", required=False))

        results = checker.check_all(skip_optional=True)

        assert "required" in results
        assert "optional" not in results

    def test_check_all_handles_exception_gracefully(self):
        checker = DependencyChecker()
        checker.register(_FakeDependency("exploding", raise_on_check=True))

        results = checker.check_all()

        assert results["exploding"].status == DependencyStatus.BROKEN

    def test_repair_failures_only_repairs_unhealthy(self):
        checker = DependencyChecker()
        healthy = _FakeDependency("healthy", DependencyStatus.HEALTHY)
        broken = _FakeDependency("broken", DependencyStatus.BROKEN)
        checker.register(healthy)
        checker.register(broken)
        checker.check_all()

        checker.repair_failures(auto_repair=True)

        assert healthy.repair_called is False
        assert broken.repair_called is True

    def test_repair_failures_respects_auto_repair_false(self):
        checker = DependencyChecker()
        broken = _FakeDependency("broken", DependencyStatus.BROKEN)
        checker.register(broken)
        checker.check_all()

        results = checker.repair_failures(auto_repair=False)

        assert broken.repair_called is False
        assert results["broken"] == (False, "Auto-repair disabled")

    def test_get_summary_counts(self):
        checker = DependencyChecker()
        checker.register(_FakeDependency("a", DependencyStatus.HEALTHY))
        checker.register(_FakeDependency("b", DependencyStatus.MISSING))
        checker.register(_FakeDependency("c", DependencyStatus.BROKEN))
        checker.check_all()

        summary = checker.get_summary()

        assert summary["total"] == 3
        assert summary["healthy"] == 1
        assert summary["missing"] == 1
        assert summary["broken"] == 1

    def test_get_summary_empty_when_nothing_checked(self):
        checker = DependencyChecker()
        summary = checker.get_summary()
        assert summary["total"] == 0
        assert summary["percentage_healthy"] == 0

    def test_export_report_shape(self):
        checker = DependencyChecker()
        checker.register(_FakeDependency("a", DependencyStatus.HEALTHY))
        checker.check_all()

        report = checker.export_report()

        assert set(report.keys()) == {"timestamp", "summary", "dependencies"}
        assert "a" in report["dependencies"]