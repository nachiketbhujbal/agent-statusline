"""Configuration behavior with disposable home, host settings, and state."""

import pytest

from agent_statusline import config, session_metrics
from agent_statusline.cli import main
from agent_statusline.hooks import context_guard


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = tmp_path / "agent-statusline" / "config.toml"
    path.parent.mkdir()
    return path


def test_config_path_ignores_relative_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert config.config_path({"XDG_CONFIG_HOME": "."}) == (
        tmp_path / ".config/agent-statusline/config.toml"
    )


def test_config_check_does_not_touch_runtime_paths(config_file, tmp_path, monkeypatch, capsys):
    state = tmp_path / "state"
    claude = tmp_path / "claude"
    monkeypatch.setenv("AGENT_STATUSLINE_STATE", str(state))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    assert main(["config", "check"]) == 0
    assert "no file; defaults apply" in capsys.readouterr().out
    sample = b'schema_version = 1\n[display.rows]\nCOST = "hide"\n'
    config_file.write_bytes(sample)
    assert main(["config", "check"]) == 0
    assert "valid" in capsys.readouterr().out
    assert config_file.read_bytes() == sample
    assert not state.exists()
    assert not claude.exists()


def test_file_values_and_per_setting_env_overrides(config_file):
    config_file.write_text(
        'schema_version = 1\n[context_guard]\nwarn_pct = 65.5\nwarn_event = "both"\n'
        'warn_message = "Now at {pct}%"\n[session_metrics]\nenabled = false\n'
    )
    environ = {"XDG_CONFIG_HOME": str(config_file.parent.parent)}
    assert context_guard.configuration(environ) == (
        {"threshold": 65.5, "event": "both", "message": "Now at {pct}%"},
        None,
    )
    environ[context_guard.EVENT_ENV] = " SUBMIT "
    environ[context_guard.THRESHOLD_ENV] = "92"
    resolved, error = context_guard.configuration(environ)
    assert error is None
    assert resolved == {"threshold": 92.0, "event": "submit", "message": "Now at {pct}%"}
    file_default = config.load_config(environ).metrics_enabled
    assert not session_metrics.enabled(environ, file_default=file_default)
    assert session_metrics.enabled(
        {**environ, session_metrics.OPT_OUT_ENV: "yes"}, file_default=file_default
    )


@pytest.mark.parametrize(
    "raw, diagnostic",
    [
        (b"schema_version = true", "schema_version"),
        (b"schema_version = 2", "schema_version"),
        (b"schema_version = 1\n[display]\nprivate_value = true", "display: unknown key"),
        (b"schema_version = 1\n[display]\nfields = []", "display.fields: expected a table"),
        (
            b"schema_version = 1\n[display.fields]\nprivate_value = []",
            "display.fields: unknown key",
        ),
        (b'schema_version = 1\n[display.fields]\nPROJECT = "branch"', "nonempty array"),
        (b"schema_version = 1\n[display.fields]\nPROJECT = []", "nonempty array"),
        (b"schema_version = 1\n[display.fields]\nPROJECT = [true]", "unknown field ID"),
        (b'schema_version = 1\n[display.fields]\nPROJECT = ["private_value"]', "unknown field ID"),
        (b'schema_version = 1\n[display.fields]\nPROJECT = ["hooks"]', "unknown field ID"),
        (
            b'schema_version = 1\n[display.fields]\nPROJECT = ["branch", "branch"]',
            "duplicate field ID",
        ),
        (b'schema_version = 1\n[display.rows]\nprivate_value = "show"', "display.rows"),
        (b"schema_version = 1\n[display.rows]\nCOST = false", "display.rows.COST"),
        (b"schema_version = 1\n[context_guard]\nwarn_pct = nan", "context_guard.warn_pct"),
        (b"schema_version = 1\n[context_guard]\nwarn_event = []", "context_guard.warn_event"),
        (
            b'schema_version = 1\n[context_guard]\nwarn_message = "private_value"',
            "context_guard.warn_message",
        ),
        (b'schema_version = 1\n[session_metrics]\nenabled = "false"', "session_metrics.enabled"),
        (b'schema_version = 1\n[display]\ncolor = "private_value"', "display.color"),
        (b"private_value =", "TOML syntax"),
        (b"\xff", "UTF-8"),
        (b" " * (config.MAX_BYTES + 1), "64 KiB"),
    ],
)
def test_bad_file_rejects_entire_file_without_echoing_values(config_file, capsys, raw, diagnostic):
    config_file.write_bytes(raw)
    assert config.load_config() == config.DEFAULTS
    assert main(["config", "check"]) == 1
    error = capsys.readouterr().err
    assert diagnostic in error
    assert "private_value" not in error


def test_invalid_file_still_allows_environment_override(config_file, monkeypatch):
    config_file.write_text(
        "schema_version = 1\n[context_guard]\nwarn_pct = 42\n[display.fields]\nCOST = []\n"
    )
    monkeypatch.setenv(context_guard.EVENT_ENV, "both")
    resolved, error = context_guard.configuration()
    assert error is None
    assert resolved == {"threshold": 80.0, "event": "both", "message": None}


def test_config_check_accepts_field_selection(config_file, capsys):
    config_file.write_text(
        'schema_version = 1\n[display.fields]\nPROJECT = ["session_name", "branch"]\n'
    )
    assert main(["config", "check"]) == 0
    assert "valid" in capsys.readouterr().out
    assert dict(config.load_config().fields) == {"PROJECT": {"session_name", "branch"}}


def test_config_path_must_be_a_regular_file(config_file, capsys):
    config_file.mkdir()
    assert config.load_config() == config.DEFAULTS
    assert main(["config", "check"]) == 1
    assert "regular configuration file" in capsys.readouterr().err
