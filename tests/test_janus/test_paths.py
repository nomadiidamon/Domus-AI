"""
Tests for Janus/paths.py

paths.py resolves two independent roots:
  - the runtime *source* data (config, Modelfiles, MCP servers/profiles),
    bundled as the DomusData/DomusMCP packages and found via
    importlib.resources. LOCAL_AI_RUNTIME_ROOT (validated through
    find_root() and .domus-marker) overrides it. The default branch is
    covered in test_packaging.py.
  - the *host project* root (get_host_project_root(), via
    .domus-host-marker) - the project this runtime instance is working
    inside, writable, created on demand.

Both are exercised here against disposable tmp_path directories rather
than the real repo checkout or a real project, via the
isolated_runtime_root / host_project_dir fixtures from the root conftest.
"""

import os

import pytest

from Janus import paths

pytestmark = pytest.mark.janus


class TestFindRoot:
    def test_finds_root_via_env_var(self, isolated_runtime_root):
        result = paths.find_root()
        assert result == isolated_runtime_root

    def test_raises_when_env_var_points_to_invalid_location(self, tmp_path, monkeypatch):
        bad_dir = tmp_path / "no_marker_here"
        bad_dir.mkdir()
        monkeypatch.setenv("LOCAL_AI_RUNTIME_ROOT", str(bad_dir))

        with pytest.raises(RuntimeError, match="LOCAL_AI_RUNTIME_ROOT"):
            paths.find_root()

    def test_finds_root_by_walking_up_from_file_location(self, monkeypatch):
        """
        Without LOCAL_AI_RUNTIME_ROOT set, find_root() (now only a
        source-checkout/override fallback) walks up from
        paths.py's own file location looking for .domus-marker - which
        in this real checkout means it should resolve to the actual
        project root (where .domus-marker genuinely lives).
        """
        monkeypatch.delenv("LOCAL_AI_RUNTIME_ROOT", raising=False)
        result = paths.find_root()
        assert (result / ".domus-marker").exists()


class TestRuntimeSourcePaths:
    """Override branch (LOCAL_AI_RUNTIME_ROOT set); see test_packaging.py for the default."""

    def test_get_modelfiles_path(self, isolated_runtime_root):
        assert paths.get_modelfiles_path() == isolated_runtime_root / "Modelfiles"

    def test_get_mcp_path(self, isolated_runtime_root):
        assert paths.get_mcp_path() == isolated_runtime_root / "mcp"

    def test_get_python_requirements_path(self, isolated_runtime_root):
        assert paths.get_python_requirements_path() == isolated_runtime_root / "requirements.txt"


class TestHostProjectRoot:
    def test_get_host_project_root_raises_when_unset(self, monkeypatch):
        monkeypatch.delenv("LOCAL_AI_RUNTIME_HOST", raising=False)
        with pytest.raises(RuntimeError, match="Host project root has not been set"):
            paths.get_host_project_root()

    def test_get_host_project_root_resolves_from_env_var(self, host_project_dir):
        result = paths.get_host_project_root()
        assert result == host_project_dir

    def test_get_host_project_root_creates_marker_file(self, host_project_dir):
        paths.get_host_project_root()
        assert (host_project_dir / ".domus-host-marker").exists()

    def test_set_host_project_root_is_picked_up_by_get(self, tmp_path):
        target = tmp_path / "explicit-host"
        target.mkdir()

        paths.set_host_project_root(target)

        assert paths.get_host_project_root() == target

    def test_set_host_project_root_raises_for_nonexistent_path(self, tmp_path):
        with pytest.raises(RuntimeError, match="does not exist"):
            paths.set_host_project_root(tmp_path / "nope")

    def test_set_host_project_root_raises_for_file_not_directory(self, tmp_path):
        a_file = tmp_path / "a_file.txt"
        a_file.write_text("hi")
        with pytest.raises(RuntimeError, match="not a directory"):
            paths.set_host_project_root(a_file)

    def test_is_host_initialized_false_when_unset(self, monkeypatch):
        monkeypatch.delenv("LOCAL_AI_RUNTIME_HOST", raising=False)
        assert paths.is_host_initialized() is False

    def test_is_host_initialized_true_when_set(self, host_project_dir):
        assert paths.is_host_initialized() is True


class TestHostMarkerExistsAt:
    """host_marker_exists_at() is a read-only disk check: no marker file,
    no .domus-AI/ dir, and no touching of the in-memory host-root cache
    or LOCAL_AI_RUNTIME_HOST. Used by initialize_host() to skip the
    interactive prompt when a directory was already initialized."""
 
    def test_false_for_empty_directory(self, tmp_path):
        assert paths.host_marker_exists_at(tmp_path) is False
 
    def test_false_when_only_marker_file_present(self, tmp_path):
        (tmp_path / ".domus-host-marker").touch()
        assert paths.host_marker_exists_at(tmp_path) is False
 
    def test_false_when_only_domus_ai_dir_present(self, tmp_path):
        (tmp_path / ".domus-AI").mkdir()
        assert paths.host_marker_exists_at(tmp_path) is False
 
    def test_true_when_marker_file_and_domus_ai_dir_present(self, tmp_path):
        (tmp_path / ".domus-host-marker").touch()
        (tmp_path / ".domus-AI").mkdir()
        assert paths.host_marker_exists_at(tmp_path) is True
 
    def test_does_not_create_anything(self, tmp_path):
        """Purely a read - must not touch the filesystem."""
        before = list(tmp_path.iterdir())
        paths.host_marker_exists_at(tmp_path)
        assert list(tmp_path.iterdir()) == before
 
    def test_does_not_set_host_cache(self, tmp_path, monkeypatch):
        """Must not populate _host_project_root or the env var as a side effect."""
        monkeypatch.delenv("LOCAL_AI_RUNTIME_HOST", raising=False)
        (tmp_path / ".domus-host-marker").touch()
        (tmp_path / ".domus-AI").mkdir()
 
        paths.host_marker_exists_at(tmp_path)
 
        assert paths.is_host_initialized() is False
 
 
class TestInitializeHostSkipsPromptWhenMarkerExists:
    def test_adopts_directory_without_prompting(self, tmp_path, monkeypatch):
        (tmp_path / ".domus-host-marker").touch()
        (tmp_path / ".domus-AI").mkdir()
 
        def _fail_if_called(*_a, **_k):
            raise AssertionError("input() must not be called when the marker already exists")
        monkeypatch.setattr("builtins.input", _fail_if_called)
 
        result = paths.initialize_host(suggested=tmp_path)
 
        assert result == tmp_path
        assert paths.get_host_project_root() == tmp_path
 
    def test_still_prompts_when_marker_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda *_a, **_k: "y")
        result = paths.initialize_host(suggested=tmp_path)
        assert result == tmp_path
        assert (tmp_path / ".domus-host-marker").exists()
 


class TestHostProjectPaths:
    def test_derived_paths_are_under_ai_runtime_dir(self, host_project_dir):
        ai_dir = paths.get_ai_runtime_dir()
        assert ai_dir == host_project_dir / ".domus-AI"
        assert paths.get_cache_dir() == ai_dir / "cache"
        assert paths.get_logs_dir() == ai_dir / "logs"
        assert paths.get_models_dir() == ai_dir / "models"
        assert paths.get_memory_dir() == ai_dir / "memory"
        assert paths.get_config_dir() == ai_dir / "config"
        assert paths.get_sessions_dir() == ai_dir / "sessions"


class TestEnsureHostDirs:
    def test_creates_all_expected_directories(self, host_project_dir):
        paths.ensure_host_dirs()

        for getter in [
            paths.get_ai_runtime_dir, paths.get_cache_dir, paths.get_logs_dir,
            paths.get_models_dir, paths.get_memory_dir, paths.get_config_dir,
            paths.get_sessions_dir,
        ]:
            assert getter().exists(), f"{getter.__name__} was not created"

    def test_idempotent(self, host_project_dir):
        paths.ensure_host_dirs()
        paths.ensure_host_dirs()  # must not raise


class TestGetDirectoryReport:
    def test_reports_missing_before_creation(self, host_project_dir):
        report = paths.get_directory_report()
        for entry in report.values():
            assert entry["exists"] is False
            assert entry["writable"] is False

    def test_reports_existing_and_writable_after_creation(self, host_project_dir):
        paths.ensure_host_dirs()
        report = paths.get_directory_report()
        for entry in report.values():
            assert entry["exists"] is True
            assert entry["writable"] is True


class TestInitializeHost:
    def test_noop_returns_existing_host_when_already_initialized(self, host_project_dir):
        result = paths.initialize_host()
        assert result == host_project_dir

    def test_non_interactive_accepts_suggested_path(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LOCAL_AI_RUNTIME_HOST", raising=False)
        suggested = tmp_path / "suggested-host"
        suggested.mkdir()

        result = paths.initialize_host(suggested=suggested, non_interactive=True)

        assert result == suggested
        assert paths.is_host_initialized() is True

    def test_non_interactive_raises_for_invalid_suggested_path(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LOCAL_AI_RUNTIME_HOST", raising=False)
        with pytest.raises(RuntimeError, match="Non-interactive init failed"):
            paths.initialize_host(suggested=tmp_path / "nope", non_interactive=True)