"""
Tests for Janus/installer.py

check_and_repair()/run_install() drive a real DependencyChecker built by
_build_checker() against real dependency objects — but we swap in a
DependencyChecker whose registered dependencies are small fakes (same
approach as test_dependencies.py's TestDependencyChecker), so nothing
here actually probes real system packages or shells out to pip/apt/brew.
"""

from unittest.mock import patch

import pytest

from Janus import installer
from Janus.dependencies import DependencyChecker, Dependency, DependencyType, DependencyStatus, DependencyCheckResult

pytestmark = pytest.mark.janus


class _FakeDependency(Dependency):
    def __init__(self, name, status, required=True, repair_success=True):
        super().__init__(name=name, dep_type=DependencyType.PYTHON_PACKAGE, required=required)
        self._status = status
        self._repair_success = repair_success

    def check(self):
        return DependencyCheckResult(name=self.name, dep_type=self.dep_type, status=self._status, version="1.0")

    def repair(self):
        if self._repair_success:
            self._status = DependencyStatus.HEALTHY
            return True, f"repaired {self.name}"
        return False, f"could not repair {self.name}"

    def get_install_instructions(self):
        return f"install {self.name} manually"


def _checker_with(*deps):
    checker = DependencyChecker()
    checker.register_many(list(deps))
    return checker


class TestBuildChecker:
    def test_registers_expected_dependency_names(self):
        checker = installer._build_checker()
        assert set(checker.dependencies.keys()) == {
            "psutil", "packaging", "python-dotenv", "nvidia-ml-py",
            "python", "ollama", "git", "claude",
        }

    def test_claude_is_optional_others_required(self):
        checker = installer._build_checker()
        for name, dep in checker.dependencies.items():
            if name == "claude":
                assert dep.required is False
            else:
                assert dep.required is True


class TestAllRequiredSatisfied:
    def test_true_when_all_required_healthy(self):
        checker = _checker_with(
            _FakeDependency("required1", DependencyStatus.HEALTHY),
            _FakeDependency("optional1", DependencyStatus.MISSING, required=False),
        )
        results = checker.check_all()
        assert installer._all_required_satisfied(checker, results) is True

    def test_false_when_a_required_dep_unhealthy(self):
        checker = _checker_with(
            _FakeDependency("required1", DependencyStatus.MISSING),
        )
        results = checker.check_all()
        assert installer._all_required_satisfied(checker, results) is False


class TestCheckAndRepair:
    def test_returns_true_without_repair_when_everything_already_healthy(self):
        checker = _checker_with(_FakeDependency("a", DependencyStatus.HEALTHY))

        with patch("Janus.installer._build_checker", return_value=checker):
            all_ok, results = installer.check_and_repair(auto_repair=True)

        assert all_ok is True
        assert results["a"].status == DependencyStatus.HEALTHY

    def test_attempts_repair_on_missing_required_dep(self):
        dep = _FakeDependency("a", DependencyStatus.MISSING, repair_success=True)
        checker = _checker_with(dep)

        with patch("Janus.installer._build_checker", return_value=checker):
            all_ok, results = installer.check_and_repair(auto_repair=True)

        # After repair, _FakeDependency flips itself to HEALTHY and the
        # re-check (checker.check_all() called again inside
        # check_and_repair) should reflect that.
        assert all_ok is True
        assert results["a"].status == DependencyStatus.HEALTHY

    def test_skips_repair_when_auto_repair_false(self):
        dep = _FakeDependency("a", DependencyStatus.MISSING, repair_success=True)
        checker = _checker_with(dep)

        with patch("Janus.installer._build_checker", return_value=checker):
            all_ok, results = installer.check_and_repair(auto_repair=False)

        # Dependency was never repaired, so it's still reported unhealthy.
        assert all_ok is False
        assert results["a"].status == DependencyStatus.MISSING

    def test_returns_false_when_repair_fails_for_required_dep(self):
        dep = _FakeDependency("a", DependencyStatus.MISSING, repair_success=False)
        checker = _checker_with(dep)

        with patch("Janus.installer._build_checker", return_value=checker):
            all_ok, results = installer.check_and_repair(auto_repair=True)

        assert all_ok is False

    def test_optional_dep_failure_does_not_block_success(self):
        checker = _checker_with(
            _FakeDependency("required1", DependencyStatus.HEALTHY),
            _FakeDependency("optional1", DependencyStatus.MISSING, required=False, repair_success=False),
        )

        with patch("Janus.installer._build_checker", return_value=checker):
            all_ok, results = installer.check_and_repair(auto_repair=True)

        assert all_ok is True


class TestRunInstall:
    def test_returns_true_when_check_and_repair_succeeds(self):
        with patch("Janus.installer.check_and_repair", return_value=(True, {})):
            result = installer.run_install()
        assert result is True

    def test_returns_false_when_check_and_repair_fails(self):
        with patch("Janus.installer.check_and_repair", return_value=(False, {})):
            result = installer.run_install()
        assert result is False

    def test_passes_through_auto_repair_flag(self):
        with patch("Janus.installer.check_and_repair", return_value=(True, {})) as mock_check:
            installer.run_install(auto_repair=False)
        mock_check.assert_called_once_with(auto_repair=False)