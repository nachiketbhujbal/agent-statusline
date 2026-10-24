"""Configurable context warning and event timing."""

import io
import json

import pytest

from agent_statusline.hooks import context_guard


@pytest.fixture
def hook_io(monkeypatch, capsys):
    actual_configuration = context_guard.configuration

    def invoke(payload, snapshot=None, environ=None):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
        monkeypatch.setattr(context_guard, "read_snapshot", lambda _sid: snapshot)
        monkeypatch.setattr(context_guard, "write_text", lambda _path, _text: None)
        monkeypatch.setattr(context_guard, "window_size", lambda _payload: 1000)
        monkeypatch.setattr(context_guard, "live_tokens", lambda _path: 850)
        monkeypatch.setattr(
            context_guard,
            "configuration",
            lambda: actual_configuration(environ),
        )
        assert context_guard.main() == 0
        output = capsys.readouterr().out
        return json.loads(output) if output else None

    return invoke


def test_default_stop_warning_prefers_session_metrics(hook_io):
    output = hook_io(
        {"hook_event_name": "Stop", "session_id": "session-1"},
        {"context_used_pct": 84.6, "context_window_size": 200_000},
        {},
    )

    assert "85% full (169,200 of 200,000 tokens)" in output["systemMessage"]
    assert "hookSpecificOutput" not in output


def test_default_submit_is_quiet(hook_io):
    assert hook_io({"hook_event_name": "UserPromptSubmit"}, environ={}) is None


def test_submit_option_uses_custom_message_as_additional_context(hook_io):
    output = hook_io(
        {"hook_event_name": "UserPromptSubmit", "transcript_path": "/synthetic"},
        environ={
            context_guard.EVENT_ENV: "submit",
            context_guard.THRESHOLD_ENV: "82.5",
            context_guard.MESSAGE_ENV: "Save the handoff now; context is {pct}% full.",
        },
    )

    assert output["systemMessage"] == "Save the handoff now; context is 85% full."
    assert output["hookSpecificOutput"] == {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "Save the handoff now; context is 85% full.",
    }


def test_both_option_warns_on_stop_and_submit(hook_io):
    environ = {context_guard.EVENT_ENV: "both"}

    assert hook_io({"hook_event_name": "Stop"}, environ=environ)["systemMessage"]
    assert hook_io({"hook_event_name": "UserPromptSubmit"}, environ=environ)["hookSpecificOutput"]


@pytest.mark.parametrize(
    "environ, expected",
    [
        ({context_guard.THRESHOLD_ENV: "zero"}, context_guard.THRESHOLD_ENV),
        ({context_guard.THRESHOLD_ENV: "0"}, context_guard.THRESHOLD_ENV),
        ({context_guard.THRESHOLD_ENV: "nan"}, context_guard.THRESHOLD_ENV),
        ({context_guard.EVENT_ENV: "later"}, context_guard.EVENT_ENV),
        ({context_guard.MESSAGE_ENV: "missing placeholder"}, context_guard.MESSAGE_ENV),
    ],
)
def test_configuration_rejects_invalid_values(environ, expected):
    config, error = context_guard.configuration(environ)

    assert config is None
    assert expected in error


def test_configuration_accepts_documented_values():
    config, error = context_guard.configuration(
        {
            context_guard.THRESHOLD_ENV: "95",
            context_guard.EVENT_ENV: "both",
            context_guard.MESSAGE_ENV: "Context is {pct}% full; write the project handoff.",
        }
    )

    assert error is None
    assert config == {
        "threshold": 95.0,
        "event": "both",
        "message": "Context is {pct}% full; write the project handoff.",
    }


def test_invalid_live_configuration_is_visible_without_blocking(hook_io):
    output = hook_io(
        {"hook_event_name": "Stop"},
        environ={context_guard.THRESHOLD_ENV: "invalid"},
    )

    assert context_guard.THRESHOLD_ENV in output["systemMessage"]
    assert "hookSpecificOutput" not in output


@pytest.mark.parametrize(
    "current, cached, expected",
    [
        ({"session_id": "one"}, {"session_id": "one"}, 200_000),
        ({"session_id": "one"}, {"session_id": "two"}, 0),
        ({"session_id": "one"}, {}, 0),
        ({}, {"session_id": "two"}, 0),
        ({"transcript_path": "/one"}, {"transcript_path": "/one"}, 200_000),
        ({"transcript_path": "/one"}, {"transcript_path": "/two"}, 0),
        (
            {"session_id": "one", "transcript_path": "/one"},
            {"session_id": "one", "transcript_path": "/old"},
            0,
        ),
    ],
)
def test_last_payload_window_requires_matching_identity(monkeypatch, current, cached, expected):
    cached["context_window"] = {"context_window_size": 200_000}
    monkeypatch.setattr(context_guard, "read_json", lambda _path, _default: cached)

    assert context_guard.window_size(current) == expected


@pytest.mark.parametrize("size", [0, -1, True, "invalid", float("inf")])
def test_matching_payload_with_invalid_window_is_unavailable(monkeypatch, size):
    monkeypatch.setattr(
        context_guard,
        "read_json",
        lambda _path, _default: {
            "session_id": "one",
            "context_window": {"context_window_size": size},
        },
    )

    assert context_guard.window_size({"session_id": "one"}) == 0


@pytest.mark.parametrize("snapshot", [None, {"context_used_pct": "invalid"}])
def test_fallback_never_uses_another_sessions_window(tmp_path, monkeypatch, snapshot):
    cached = tmp_path / "last-payload.json"
    path = tmp_path / "one.jsonl"
    path.write_text(
        json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 170_000}}}) + "\n"
    )
    monkeypatch.setattr(context_guard, "state", lambda _name: cached)
    monkeypatch.setattr(context_guard, "read_snapshot", lambda _sid: snapshot)
    current = {"session_id": "one", "transcript_path": str(path)}
    for session, size, expected in [
        ("two", 1_000_000, None),
        ("one", 200_000, (85.0, 170_000, 200_000)),
        ("two", 200_000, None),
    ]:
        cached.write_text(
            json.dumps(
                {
                    "session_id": session,
                    "transcript_path": str(path),
                    "context_window": {"context_window_size": size},
                }
            )
        )
        assert context_guard.context_usage(current) == expected
