"""
Tests for Faber/models.py

start_model/stop_model shell out to `ollama run <model>` via
subprocess.Popen and optionally notify a bound RuntimeContext
(set via set_context) of load/unload events. Both subprocess.Popen and
the context are faked here so tests never spawn real processes or
depend on Mentis.context being importable/side-effect-free.

Model management commands mock subprocesses or HTTP so no real Ollama
binary or network access is needed. build_model's Modelfile resolution
(_resolve_modelfile) is tested separately with Janus.config/Janus.paths patched out.
"""

import subprocess
import io
import json
from unittest.mock import patch, MagicMock
import urllib.error

import pytest

import Faber.models as models_module
from Faber.models import (
    start_model,
    stop_model,
    pull_model,
    build_model,
    list_models,
    remove_model,
    set_context,
)
from Faber.session import get_session

pytestmark = pytest.mark.faber


class TestStartModel:
    def test_spawns_ollama_run_with_model_name(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process) as mock_popen:
            result = start_model("mercury")

        args, kwargs = mock_popen.call_args
        assert args[0] == ["ollama", "run", "mercury"]
        assert result is fake_process

    def test_creates_session_named_after_model(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")
        assert get_session("mercury") is not None

    def test_returns_existing_session_without_spawning_again(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process) as mock_popen:
            start_model("mercury")
            second = start_model("mercury")

        assert mock_popen.call_count == 1
        # NOTE: unlike start_ollama, start_model's early-return path
        # returns the *Session* object, not the process, when the model
        # is already running - this asymmetry is intentional per the
        # current implementation, so we pin it rather than "fixing" it.
        assert second is get_session("mercury")

    def test_notifies_bound_context_on_start(self, fake_process):
        fake_context = MagicMock()
        set_context(fake_context)

        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")

        fake_context.load_model.assert_called_once()
        call_args = fake_context.load_model.call_args
        assert call_args[0][0] == "mercury"

    def test_no_context_call_when_none_bound(self, fake_process):
        # _reset_faber_models_context autouse fixture guarantees _context
        # is None at the start of this test.
        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")  # must not raise even with no context bound


class TestStopModel:
    def test_stop_model_terminates_session(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")

        stop_model("mercury")

        assert fake_process.terminated is True
        assert get_session("mercury") is None

    def test_stop_model_notifies_bound_context(self, fake_process):
        fake_context = MagicMock()
        set_context(fake_context)

        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")
        stop_model("mercury")

        fake_context.unload_model.assert_called_once_with("mercury")

    def test_stop_model_no_context_call_when_model_was_not_running(self):
        fake_context = MagicMock()
        set_context(fake_context)

        stop_model("never_started")

        fake_context.unload_model.assert_not_called()


class TestSetContext:
    def test_set_context_binds_module_level_context(self):
        fake_context = MagicMock()
        set_context(fake_context)
        assert models_module._context is fake_context


class TestEventBusChain:
    """start_model/stop_model with a bound RuntimeContext must surface on
    the DomusEvents bus via Mentis' log_event bridge (Faber -> Mentis ->
    DomusEvents), not just via Janus' CLI handlers."""

    @pytest.fixture
    def bus(self):
        import DomusEvents
        bus = DomusEvents.initialize_bus()
        yield bus
        DomusEvents.shutdown_bus(drain=False)

    def test_start_then_stop_publishes_load_and_unload_events(self, fake_process, bus):
        import DomusEvents
        from Mentis.context import RuntimeContext

        loaded, unloaded = [], []
        bus.subscribe(DomusEvents.EventType.MODEL_LOADED, loaded.append)
        bus.subscribe(DomusEvents.EventType.MODEL_UNLOADED, unloaded.append)

        set_context(RuntimeContext(project_name="ChainTest"))

        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")
        stop_model("mercury")

        bus.stop(drain=True)

        assert len(loaded) == 1
        assert len(unloaded) == 1
        assert loaded[0].source == "mentis"


class TestPullModel:
    def test_runs_ollama_pull(self):
        response = MagicMock()
        response.__enter__.return_value = [b'{"status":"pulling","completed":5,"total":10}\n']
        with patch("urllib.request.urlopen", return_value=response) as mock_urlopen:
            pull_model("mercury")

        request = mock_urlopen.call_args.args[0]
        assert request.full_url == "http://localhost:11434/api/pull"
        assert json.loads(request.data) == {"name": "mercury", "stream": True}

    def test_reports_streamed_progress_to_tracker(self):
        from Hestia.software.installer import InstallActionStatus

        response = MagicMock()
        response.__enter__.return_value = [
            b'{"status":"pulling layers","completed":25,"total":100}\n',
        ]
        events = []
        with patch("urllib.request.urlopen", return_value=response):
            pull_model("mercury", progress=events.append)

        assert [event.completed for event in events] == [0.0, 0.25, 1.0]
        assert events[-1].status is InstallActionStatus.SUCCEEDED

    def test_uses_install_progress_tracker_by_default(self):
        response = MagicMock()
        response.__enter__.return_value = [b'{"status":"pulling"}\n']
        tracker = MagicMock()
        with patch("Hestia.software.installer.InstallProgressTracker", return_value=tracker) as factory, \
             patch("urllib.request.urlopen", return_value=response):
            pull_model("mercury")

        factory.assert_called_once_with()
        assert tracker.call_count == 3

    def test_raises_on_nonzero_exit(self):
        response = io.BytesIO(b'{"error":"no such model"}')
        error = urllib.error.HTTPError("url", 400, "Bad Request", {}, response)
        with patch("urllib.request.urlopen", side_effect=error):
            with pytest.raises(RuntimeError, match="no such model"):
                pull_model("mercury")

    def test_raises_when_ollama_server_unreachable(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            with pytest.raises(RuntimeError, match="Ollama server unreachable"):
                pull_model("mercury")

    def test_raises_on_timeout(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError):
            with pytest.raises(RuntimeError, match="timed out"):
                pull_model("mercury")


class TestResolveModelfile:
    def test_uses_config_path_when_it_exists(self, tmp_path):
        modelfile = tmp_path / "Modelfile"
        modelfile.write_text("FROM base\n")

        with patch("Janus.config.get_model_config", return_value={"modelfile": str(modelfile)}):
            assert models_module._resolve_modelfile("mercury") == modelfile

    def test_case_insensitive_config_lookup(self, tmp_path):
        modelfile = tmp_path / "Modelfile"
        modelfile.write_text("FROM base\n")

        with patch("Janus.config.get_model_config", return_value=None), \
             patch("Janus.config.load_models_config", return_value={"Mercury": {"modelfile": str(modelfile)}}):
            assert models_module._resolve_modelfile("mercury") == modelfile

    def test_falls_back_to_repo_modelfiles_dir(self, tmp_path):
        fallback = tmp_path / "Mercury" / "Modelfile.Mercury"
        fallback.parent.mkdir(parents=True)
        fallback.write_text("FROM base\n")

        with patch("Janus.config.get_model_config", return_value=None), \
             patch("Janus.config.load_models_config", return_value={}), \
             patch("Janus.paths.get_modelfiles_path", return_value=tmp_path):
            assert models_module._resolve_modelfile("mercury") == fallback

    def test_raises_when_no_modelfile_found(self, tmp_path):
        with patch("Janus.config.get_model_config", return_value=None), \
             patch("Janus.config.load_models_config", return_value={}), \
             patch("Janus.paths.get_modelfiles_path", return_value=tmp_path):
            with pytest.raises(RuntimeError, match="No Modelfile found"):
                models_module._resolve_modelfile("mercury")

    def test_resolves_real_repo_modelfile_for_configured_models(self):
        """Smoke test against the real repo layout: every model named in
        config/models.json must resolve to an on-disk Modelfile, whether
        via the configured path or the Modelfiles/<Name>/Modelfile.<Name>
        fallback. Uses the real Janus.config/Janus.paths (no mocks) so it
        catches root-marker or directory-layout breakage that the mocked
        tests above cannot."""
        from Janus.config import load_models_config

        configured = load_models_config()
        if not configured:
            pytest.skip("no models configured in models.json")

        for name in configured:
            path = models_module._resolve_modelfile(name)
            assert path.is_file(), f"{name}: resolved Modelfile {path} does not exist"


class TestBuildModel:
    def test_runs_ollama_create_with_resolved_modelfile(self, tmp_path):
        from Hestia.software.installer import InstallActionStatus

        modelfile = tmp_path / "Modelfile.Mercury"
        modelfile.write_text('FROM base\nSYSTEM """\nYou are helpful.\n"""\nPARAMETER temperature 0.2\nPARAMETER num_ctx 8192\n')
        response = MagicMock()
        response.__enter__.return_value = [
            b'{"status":"pulling","completed":25,"total":100}\n',
            b'{"status":"success"}\n',
        ]
        events = []

        with patch.object(models_module, "_resolve_modelfile", return_value=modelfile), \
             patch("urllib.request.urlopen", return_value=response) as mock_urlopen:
            build_model("mercury", progress=events.append)

        request = mock_urlopen.call_args.args[0]
        assert request.full_url == "http://localhost:11434/api/create"
        assert json.loads(request.data) == {
            "model": "mercury", "stream": True, "from": "base",
            "system": "You are helpful.",
            "parameters": {"temperature": 0.2, "num_ctx": 8192},
        }
        assert [event.completed for event in events] == [0.0, 0.25, None, 1.0]
        assert events[-1].status is InstallActionStatus.SUCCEEDED

    def test_bundled_modelfiles_produce_create_fields(self):
        from Janus.config import load_models_config

        for name in load_models_config():
            path = models_module._resolve_modelfile(name)
            fields = models_module._modelfile_create_fields(path.read_text(encoding="utf-8"))
            assert fields["from"]
            assert fields["system"]
            assert fields["parameters"]

    def test_raises_when_no_modelfile_found(self):
        with patch.object(models_module, "_resolve_modelfile", side_effect=RuntimeError("No Modelfile found")):
            with pytest.raises(RuntimeError, match="No Modelfile found"):
                build_model("mercury")

    def test_raises_on_build_failure(self, tmp_path):
        from Hestia.software.installer import InstallActionStatus

        modelfile = tmp_path / "Modelfile"
        modelfile.write_text("FROM base\n")
        response = MagicMock()
        response.__enter__.return_value = [b'{"error":"base not found"}\n']
        events = []
        with patch.object(models_module, "_resolve_modelfile", return_value=modelfile), \
               patch("urllib.request.urlopen", return_value=response):
            with pytest.raises(RuntimeError, match="base not found"):
                build_model("mercury", progress=events.append)
        assert events[-1].status is InstallActionStatus.FAILED

    @pytest.mark.parametrize("content, message", [
        ("SYSTEM hello\n", "FROM directive"),
        ("FROM base\nTEMPLATE hello\n", "Unsupported Modelfile directive: TEMPLATE"),
        ("FROM base\nPARAMETER mystery 1\n", "Unsupported Modelfile parameter: mystery"),
        ("FROM base\nPARAMETER num_ctx invalid\n", "Invalid value"),
        ('FROM base\nSYSTEM """unfinished\n', "Unterminated SYSTEM"),
        ("FROM ./model.gguf\n", "Local model files"),
        ("FROM base\nFROM other\n", "Multiple FROM"),
    ])
    def test_rejects_unsupported_or_invalid_modelfiles(self, tmp_path, content, message):
        modelfile = tmp_path / "Modelfile"
        modelfile.write_text(content)
        with patch.object(models_module, "_resolve_modelfile", return_value=modelfile), \
             patch("urllib.request.urlopen") as mock_urlopen:
            with pytest.raises(RuntimeError, match=message):
                build_model("mercury", progress=lambda event: None)
        mock_urlopen.assert_not_called()

    def test_repeated_stop_parameters_are_preserved(self):
        fields = models_module._modelfile_create_fields(
            'FROM base\nPARAMETER stop "first stop"\nPARAMETER stop second\n'
        )
        assert fields["parameters"]["stop"] == ["first stop", "second"]


class TestListModels:
    def test_parses_ollama_list_output(self):
        stdout = (
            "NAME            ID              SIZE      MODIFIED\n"
            "mercury:latest  abc123          4.7 GB    3 days ago\n"
        )
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=stdout, stderr="")
            models = list_models()

        assert models == [{
            "name": "mercury:latest",
            "id": "abc123",
            "size": "4.7 GB",
            "modified": "3 days ago",
        }]

    def test_empty_output_returns_empty_list(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="NAME  ID  SIZE  MODIFIED\n", stderr="")
            assert list_models() == []

    def test_raises_on_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="connection refused")
            with pytest.raises(RuntimeError, match="connection refused"):
                list_models()


class TestRemoveModel:
    def test_runs_ollama_rm(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            remove_model("mercury")

        assert mock_run.call_args[0][0] == ["ollama", "rm", "mercury"]

    def test_terminates_and_drops_tracked_session(self, fake_process):
        with patch("subprocess.Popen", return_value=fake_process):
            start_model("mercury")
        assert get_session("mercury") is not None

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            remove_model("mercury")

        assert fake_process.terminated is True
        assert get_session("mercury") is None

    def test_raises_on_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="model not found")
            with pytest.raises(RuntimeError, match="model not found"):
                remove_model("mercury")