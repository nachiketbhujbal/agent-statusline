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
    assert resolved == {
        "threshold": 92.0,
        "event": "submit",
        "message": "Now at {pct}%",
    }
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
        (
            b"schema_version = 1\n[display]\nprivate_value = true",
            "display: unknown key",
        ),
        (
            b"schema_version = 1\n[display]\nfields = []",
            "display.fields: expected a table",
        ),
        (
            b"schema_version = 1\n[display.fields]\nprivate_value = []",
            "display.fields: unknown key",
        ),
        (b'schema_version = 1\n[display.fields]\nPROJECT = "branch"', "nonempty array"),
        (b"schema_version = 1\n[display.fields]\nPROJECT = []", "nonempty array"),
        (b"schema_version = 1\n[display.fields]\nPROJECT = [true]", "unknown field ID"),
        (
            b'schema_version = 1\n[display.fields]\nPROJECT = ["private_value"]',
            "unknown field ID",
        ),
        (
            b'schema_version = 1\n[display.fields]\nPROJECT = ["hooks"]',
            "unknown field ID",
        ),
        (
            b'schema_version = 1\n[display.fields]\nPROJECT = ["branch", "branch"]',
            "duplicate field ID",
        ),
        (b'schema_version = 1\n[display.rows]\nprivate_value = "show"', "display.rows"),
        (b"schema_version = 1\n[display.rows]\nCOST = false", "display.rows.COST"),
        (
            b"schema_version = 1\n[context_guard]\nwarn_pct = nan",
            "context_guard.warn_pct",
        ),
        (
            b"schema_version = 1\n[context_guard]\nwarn_event = []",
            "context_guard.warn_event",
        ),
        (
            b'schema_version = 1\n[context_guard]\nwarn_message = "private_value"',
            "context_guard.warn_message",
        ),
        (
            b'schema_version = 1\n[session_metrics]\nenabled = "false"',
            "session_metrics.enabled",
        ),
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


@pytest.mark.parametrize("raw", [None, b"malformed TOML"])
def test_config_fields_lists_catalog_without_reading_config(
    config_file, tmp_path, monkeypatch, capsys, raw
):
    if raw is not None:
        config_file.write_bytes(raw)
    state = tmp_path / "state"
    claude = tmp_path / "claude"
    monkeypatch.setenv("AGENT_STATUSLINE_STATE", str(state))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    assert main(["config", "fields"]) == 0
    output = capsys.readouterr()
    headers = [line for line in output.out.splitlines() if not line.startswith(" ")]
    assert headers == list(config.ROW_IDS)
    assert "  compactions  Context compaction count" in output.out
    assert not output.err
    assert not state.exists() and not claude.exists()


def test_config_fields_limits_output_to_one_row(capsys):
    assert main(["config", "fields", "PROJECT"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "PROJECT",
        "  directory  Project directory and current subdirectory",
        "  added_dirs  Additional workspace directories",
        "  branch  Git branch and working tree status",
        "  session_name  Session title",
    ]


@pytest.mark.parametrize("args", [["project"], ["PROJECT", "MODEL"]])
def test_config_fields_rejects_unknown_row_and_extra_arguments(capsys, args):
    assert main(["config", "fields", *args]) == 2
    assert not capsys.readouterr().out


def test_config_show_resolves_settings_and_sources(config_file, tmp_path, monkeypatch, capsys):
    config_file.write_text(
        "schema_version = 1\n[context_guard]\nwarn_pct = 80\n"
        'warn_message = "do not print this {pct}"\n'
        '[session_metrics]\nenabled = false\n[display]\ncolor = "plain"\n'
        '[display.rows]\nCACHE = "show"\n'
        '[display.fields]\nPROJECT = ["session_name", "branch"]\n'
    )
    state = tmp_path / "state"
    claude = tmp_path / "claude"
    monkeypatch.setenv("AGENT_STATUSLINE_STATE", str(state))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(claude))
    monkeypatch.delenv(context_guard.THRESHOLD_ENV, raising=False)
    monkeypatch.delenv(context_guard.MESSAGE_ENV, raising=False)
    monkeypatch.setenv(context_guard.EVENT_ENV, " BOTH ")
    monkeypatch.setenv(session_metrics.OPT_OUT_ENV, "yes")
    assert main(["config", "show"]) == 0
    output = capsys.readouterr()
    assert "configuration: TOML loaded" in output.out
    assert "context_guard.warn_pct = 80.0 [TOML]" in output.out
    assert f"context_guard.warn_event = both [{context_guard.EVENT_ENV}]" in output.out
    assert "context_guard.warn_message = custom (redacted) [TOML]" in output.out
    assert "do not print this" not in output.out
    assert f"session_metrics.enabled = true [{session_metrics.OPT_OUT_ENV}]" in output.out
    assert "display.color = plain [TOML]" in output.out
    assert "display.rows.CACHE = show [TOML]" in output.out
    assert "display.fields.PROJECT = branch, session_name [TOML]" in output.out
    assert "display.fields.COST = all [default]" in output.out
    assert not output.err
    assert not state.exists() and not claude.exists()


def test_config_show_reports_invalid_file_and_invalid_environment(config_file, monkeypatch, capsys):
    config_file.write_text('schema_version = 1\n[display]\ncolor = "private_value"\n')
    monkeypatch.setenv(context_guard.EVENT_ENV, "private_value")
    assert main(["config", "show"]) == 0
    output = capsys.readouterr().out
    assert "Using defaults and environment" in output
    assert f"context_guard: disabled ({context_guard.EVENT_ENV}" in output
    assert "display.color = default [default]" in output
    assert "private_value" not in output


def test_config_show_reports_no_file_and_redacts_environment_message(
    config_file, monkeypatch, capsys
):
    assert not config_file.exists()
    monkeypatch.delenv(context_guard.THRESHOLD_ENV, raising=False)
    monkeypatch.delenv(context_guard.EVENT_ENV, raising=False)
    monkeypatch.setenv(context_guard.MESSAGE_ENV, "secret {pct}")
    assert main(["config", "show"]) == 0
    output = capsys.readouterr().out
    assert "configuration: no file" in output
    assert "context_guard.warn_pct = 80.0 [default]" in output
    assert f"context_guard.warn_message = custom (redacted) [{context_guard.MESSAGE_ENV}]" in output
    assert "secret" not in output
