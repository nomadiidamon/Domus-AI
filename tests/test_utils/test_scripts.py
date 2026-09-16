"""
Tests for the platform launcher scripts under scripts/.

These are static wiring checks, not executions (the .bat files can't run
on Linux): every script must invoke the correct Janus CLI command, model
aliases must delegate to the generic Start-AI script, and the script set
must stay in parity across platforms. If someone adds a CLI command or a
script, these tests force the wiring to stay honest.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO_ROOT / "scripts"

pytestmark = pytest.mark.utils

WINDOWS_BAT = SCRIPTS / "Windows" / "bat"
LINUX = SCRIPTS / "Linux"
MACOS = SCRIPTS / "MacOS"


def _read(path: Path) -> str:
    return path.read_text(errors="replace")


class TestWindowsBatScripts:
    """Each .bat must call the Python API directly (no .ps1 delegation)."""

    @pytest.mark.parametrize("script,command", [
        ("Start-AI.bat", "start"),
        ("Stop-AI.bat", "stop"),
        ("Status-AI.bat", "status"),
        ("Build-AI.bat", "build"),
        ("Pull-AI.bat", "pull"),
        ("List-AI.bat", "list"),
        ("Remove-AI.bat", "remove"),
    ])
    def test_script_invokes_janus_command(self, script, command):
        content = _read(WINDOWS_BAT / script)
        assert f"python -m Janus {command}" in content

    def test_run_tests_invokes_python_runner(self):
        content = _read(WINDOWS_BAT / "Run-Tests.bat")
        assert "run_tests.py" in content

    def test_no_bat_delegates_to_ps1(self):
        """The ps1 maintenance path was removed - nothing may reference it."""
        for bat in WINDOWS_BAT.glob("*.bat"):
            content = _read(bat)
            assert ".ps1" not in content, f"{bat.name} still references a .ps1 script"
            assert "ps1" not in [p.name for p in (SCRIPTS / "Windows").iterdir() if p.is_dir()]

    def test_ps1_directory_is_gone(self):
        assert not (SCRIPTS / "Windows" / "ps1").exists()

    @pytest.mark.parametrize("alias,model", [
        ("Start-AI-Mercury.bat", "mercury"),
        ("Start-AI-Minerva.bat", "minerva"),
        ("Start-AI-Vulcan.bat", "vulcan"),
    ])
    def test_model_aliases_delegate_to_generic_start(self, alias, model):
        content = _read(WINDOWS_BAT / alias)
        assert "Start-AI.bat" in content
        assert model in content

    def test_janus_bat_falls_back_to_python_module(self):
        content = _read(WINDOWS_BAT / "Janus.bat")
        assert "python -m Janus" in content


class TestShellScripts:
    """Linux and macOS share the same script set and structure."""

    EXPECTED = {
        "Start-AI.sh", "Start-AI-Mercury.sh", "Start-AI-Minerva.sh",
        "Start-AI-Vulcan.sh", "Stop-AI.sh", "Status-AI.sh", "Build-AI.sh",
        "Pull-AI.sh", "Remove-AI.sh", "List-AI.sh", "Run-Tests.sh",
        "Janus.sh", "Add-DomusToPath.sh", "Remove-DomusFromPath.sh",
    }

    @pytest.mark.parametrize("platform_dir", [LINUX, MACOS])
    def test_expected_scripts_present(self, platform_dir):
        present = {p.name for p in platform_dir.glob("*.sh")}
        missing = self.EXPECTED - present
        assert not missing, f"{platform_dir.name} missing: {missing}"

    @pytest.mark.parametrize("platform_dir", [LINUX, MACOS])
    @pytest.mark.parametrize("script,command", [
        ("Start-AI.sh", "start"),
        ("Stop-AI.sh", "stop"),
        ("Status-AI.sh", "status"),
        ("Build-AI.sh", "build"),
        ("Pull-AI.sh", "pull"),
        ("List-AI.sh", "list"),
        ("Remove-AI.sh", "remove"),
    ])
    def test_script_invokes_janus_command(self, platform_dir, script, command):
        content = _read(platform_dir / script)
        assert re.search(rf"python[\s\S]*-m Janus {command}\b", content)

    @pytest.mark.parametrize("platform_dir", [LINUX, MACOS])
    def test_run_tests_invokes_python_runner(self, platform_dir):
        assert "run_tests.py" in _read(platform_dir / "Run-Tests.sh")

    @pytest.mark.parametrize("platform_dir", [LINUX, MACOS])
    @pytest.mark.parametrize("alias,model", [
        ("Start-AI-Mercury.sh", "mercury"),
        ("Start-AI-Minerva.sh", "minerva"),
        ("Start-AI-Vulcan.sh", "vulcan"),
    ])
    def test_model_aliases_delegate_to_generic_start(self, platform_dir, alias, model):
        content = _read(platform_dir / alias)
        assert "Start-AI.sh" in content
        assert model in content

    @pytest.mark.parametrize("platform_dir", [LINUX, MACOS])
    def test_all_shell_scripts_pass_syntax_check(self, platform_dir):
        import subprocess
        for script in platform_dir.glob("*.sh"):
            result = subprocess.run(
                ["bash", "-n", str(script)], capture_output=True, text=True
            )
            assert result.returncode == 0, f"{script.name}: {result.stderr}"

    def test_linux_and_macos_scripts_are_identical_where_shared(self):
        """The AI lifecycle scripts are platform-identical bash; drift
        between Linux/MacOS copies is a maintenance bug."""
        shared = self.EXPECTED - {"Add-DomusToPath.sh", "Remove-DomusFromPath.sh", "Janus.sh"}
        for name in shared:
            assert _read(LINUX / name) == _read(MACOS / name), (
                f"{name} differs between Linux and MacOS"
            )


class TestCliCommandCoverage:
    """Every Janus CLI command should have a launcher somewhere."""

    def test_every_documented_command_has_script_coverage(self):
        commands = ["start", "stop", "status", "build", "pull", "list", "remove"]
        all_scripts = "\n".join(
            _read(p) for p in list(WINDOWS_BAT.glob("*.bat"))
            + list(LINUX.glob("*.sh")) + list(MACOS.glob("*.sh"))
        )
        for command in commands:
            assert f"-m Janus {command}" in all_scripts, (
                f"no launcher script covers 'janus {command}'"
            )
