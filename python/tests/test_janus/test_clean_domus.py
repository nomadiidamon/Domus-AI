import importlib.util
import subprocess
from pathlib import Path
from unittest.mock import call, patch

import pytest


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "clean_domus.py"
SPEC = importlib.util.spec_from_file_location("clean_domus", SCRIPT_PATH)
clean_domus = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(clean_domus)

INSTALL_SPEC = importlib.util.spec_from_file_location(
    "domus_install_entry", SCRIPT_PATH.parents[1] / "install.py"
)
install_entry = importlib.util.module_from_spec(INSTALL_SPEC)
INSTALL_SPEC.loader.exec_module(install_entry)

pytestmark = pytest.mark.janus


def test_python_interpreters_include_invoking_python_and_repo_venv(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    python_root = repo_root / "python"
    venv_python = repo_root / ".venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.touch()
    invoking_python = tmp_path / "system-python"
    invoking_python.touch()
    monkeypatch.setattr(clean_domus, "REPO_ROOT", python_root)
    monkeypatch.setattr(clean_domus.sys, "executable", str(invoking_python))

    assert clean_domus.python_interpreters() == [invoking_python.resolve(), venv_python.resolve()]


def test_uninstall_checks_and_uninstalls_each_interpreter(monkeypatch, tmp_path):
    interpreters = [tmp_path / "system-python", tmp_path / "venv-python"]
    monkeypatch.setattr(clean_domus, "python_interpreters", lambda: interpreters)
    check_results = [
        subprocess.CompletedProcess([], 0, stdout="domus-ai", stderr=""),
        subprocess.CompletedProcess([], 1, stdout="", stderr=""),
    ]
    uninstall_result = subprocess.CompletedProcess([], 0)
    with patch.object(clean_domus.subprocess, "run", side_effect=[check_results[0], uninstall_result, check_results[1]]) as run:
        clean_domus.uninstall()

    assert run.call_args_list == [
        call([str(interpreters[0]), "-m", "pip", "show", "domus-ai"], capture_output=True, text=True),
        call([str(interpreters[0]), "-m", "pip", "uninstall", "-y", "domus-ai"]),
        call([str(interpreters[1]), "-m", "pip", "show", "domus-ai"], capture_output=True, text=True),
    ]


def test_install_entry_installs_local_package_before_prerequisite_check(monkeypatch, tmp_path):
    steps = []

    def run_prerequisite_check(**kwargs):
        steps.append("prerequisites")
        return True

    def run_pip(command):
        steps.append("package")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(install_entry, "run_install", run_prerequisite_check)
    monkeypatch.setattr(install_entry, "__file__", str(tmp_path / "install.py"))
    monkeypatch.setattr(install_entry.sys, "argv", ["install.py"])
    with patch.object(install_entry.subprocess, "run", side_effect=run_pip) as run:
        assert install_entry.main() == 0
    assert steps == ["package", "prerequisites"]
    run.assert_called_once_with([
        install_entry.sys.executable,
        "-m", "pip", "install", "-e", f"{tmp_path}[dev]",
    ])


@pytest.mark.parametrize("flag", ["--check-only", "--no-repair"])
def test_install_entry_check_only_does_not_install_package(monkeypatch, flag):
    monkeypatch.setattr(install_entry, "run_install", lambda **kwargs: True)
    monkeypatch.setattr(install_entry.sys, "argv", ["install.py", flag])
    with patch.object(install_entry.subprocess, "run") as run:
        assert install_entry.main() == 0
    run.assert_not_called()