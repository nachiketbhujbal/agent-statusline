"""Public per-session metrics snapshots and query behavior."""

import json
import os
import stat
import subprocess
import sys

import pytest

from agent_statusline import session_metrics
from agent_statusline.acquisition import claude_facts


def facts(session_id="session-1"):
    return {
        "host": "claude",
        "transcript_path": "/synthetic/transcript.jsonl",
        "identity": {"session_id": session_id, "session_title": "Synthetic session"},
        "model": {"id": "claude-synthetic", "display_name": "Synthetic Opus"},
        "context": {"used_percentage": 42.5, "window_size": 200_000},
        "activity": {"turns": 7},
        "money": {"run_cost_usd": 1.5, "lines_added": 12, "lines_removed": 3},
    }


def aggregate():
    return {
        "session": 4.25,
        "session_complete": True,
        "started": "2026-09-15T10:00:00-04:00",
    }


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    monkeypatch.setattr(session_metrics, "state", lambda name: str(tmp_path / name))
    monkeypatch.delenv(session_metrics.OPT_OUT_ENV, raising=False)
    return tmp_path


def test_snapshot_has_the_documented_shape_and_private_file(isolated_state):
    snapshot = session_metrics.write_snapshot(facts(), aggregate(), now=1_800_000_000)

    assert snapshot == {
        "schema_version": 1,
        "producer": "agent-statusline",
        "producer_version": session_metrics.__version__,
        "session_id": "session-1",
        "host": "claude",
        "model": "Synthetic Opus",
        "context_used_pct": 42.5,
        "context_window_size": 200_000,
        "turns": 7,
        "lines_added": 12,
        "lines_removed": 3,
        "session_title": "Synthetic session",
        "started_at": "2026-09-15T10:00:00-04:00",
        "updated_at": session_metrics.ledger.iso(1_800_000_000),
        "cost_usd": 4.25,
    }
    path = isolated_state / session_metrics.filename_for("session-1")
    assert json.loads(path.read_text()) == snapshot
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert session_metrics.read_snapshot("session-1") == snapshot


def test_snapshot_omits_money_without_a_complete_exact_session(isolated_state):
    normalized = facts()
    normalized["money"] = {"lines_added": 1, "lines_removed": 0}
    result = aggregate()
    result["session_complete"] = False

    snapshot = session_metrics.write_snapshot(normalized, result, now=1_800_000_000)

    assert "cost_usd" not in snapshot


def test_snapshot_omits_a_malformed_host_cost(isolated_state):
    normalized = claude_facts(
        {"session_id": "session-1", "cost": {"total_cost_usd": float("nan")}},
        transcript_reader=lambda _path: {},
    )

    snapshot = session_metrics.write_snapshot(normalized, aggregate(), now=1_800_000_000)

    assert "run_cost_usd" not in normalized["money"]
    assert "cost_usd" not in snapshot


def test_snapshot_omits_optional_facts_that_are_unknown(isolated_state):
    normalized = {
        "host": "claude",
        "identity": {"session_id": "session-1"},
        "model": {},
        "context": {},
        "activity": {},
        "money": {},
    }

    snapshot = session_metrics.write_snapshot(
        normalized, {"session_complete": True}, now=1_800_000_000
    )

    assert set(snapshot) == {
        "schema_version",
        "producer",
        "producer_version",
        "session_id",
        "host",
        "updated_at",
    }


def test_opt_out_writes_nothing(isolated_state, monkeypatch):
    monkeypatch.setenv(session_metrics.OPT_OUT_ENV, "off")

    assert session_metrics.write_snapshot(facts(), aggregate()) is None
    assert list(isolated_state.iterdir()) == []


def test_missing_session_id_writes_nothing(isolated_state):
    normalized = facts("")

    assert session_metrics.write_snapshot(normalized, aggregate()) is None
    assert list(isolated_state.iterdir()) == []


def test_retention_prunes_oldest_session_files(isolated_state, monkeypatch):
    monkeypatch.setattr(session_metrics, "PRUNE_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(session_metrics, "RETENTION_SECONDS", 10_000)
    monkeypatch.setattr(session_metrics, "MAX_SESSION_FILES", 2)

    for number in range(3):
        session_metrics.write_snapshot(
            facts(f"session-{number}"), aggregate(), now=1_800_000_000 + number
        )

    remaining = {
        path.name
        for path in isolated_state.glob(
            f"{session_metrics.FILE_PREFIX}*{session_metrics.FILE_SUFFIX}"
        )
    }
    assert remaining == {
        session_metrics.filename_for("session-1"),
        session_metrics.filename_for("session-2"),
    }


def test_prune_does_not_delete_a_snapshot_refreshed_after_selection(isolated_state, monkeypatch):
    stale_time = 1_700_000_000
    now = stale_time + session_metrics.RETENTION_SECONDS + 1
    session_metrics.write_snapshot(facts("stale"), aggregate(), now=stale_time)
    path = isolated_state / session_metrics.filename_for("stale")
    actual_remove = session_metrics.remove_json_if
    refreshed = False

    def refresh_before_remove(selected_path, predicate):
        nonlocal refreshed
        if not refreshed:
            refreshed = True
            session_metrics.write_snapshot(facts("stale"), aggregate(), now=now)
        return actual_remove(selected_path, predicate)

    monkeypatch.setattr(session_metrics, "remove_json_if", refresh_before_remove)

    session_metrics._prune(now, keep="")

    assert path.exists()
    assert json.loads(path.read_text())["updated_at"] == session_metrics.ledger.iso(now)


def test_query_prints_one_snapshot(isolated_state, capsys):
    expected = session_metrics.write_snapshot(facts(), aggregate(), now=1_800_000_000)

    assert session_metrics.cli(["session-1"]) == 0
    assert json.loads(capsys.readouterr().out) == expected


def test_query_reports_missing_and_bad_usage(isolated_state, capsys):
    assert session_metrics.cli([]) == 2
    assert "usage:" in capsys.readouterr().err
    assert session_metrics.cli(["missing"]) == 1
    assert "no metrics" in capsys.readouterr().err


def test_concurrent_sessions_publish_complete_independent_files(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir(mode=0o700)
    env = dict(os.environ)
    env["AGENT_STATUSLINE_STATE"] = str(state_dir)
    env["PYTHONPATH"] = os.path.abspath("src")
    code = r"""
import sys
from agent_statusline.session_metrics import write_snapshot

sid = f"session-{sys.argv[1]}"
write_snapshot(
    {
        "host": "claude",
        "identity": {"session_id": sid},
        "model": {"id": "synthetic"},
        "context": {"used_percentage": 10, "window_size": 1000},
        "activity": {"turns": 1},
        "money": {"run_cost_usd": 1},
    },
    {"session": 1, "session_complete": True},
)
"""
    processes = [
        subprocess.Popen([sys.executable, "-c", code, str(number)], env=env) for number in range(8)
    ]

    assert [process.wait(timeout=20) for process in processes] == [0] * 8
    for number in range(8):
        path = state_dir / session_metrics.filename_for(f"session-{number}")
        assert json.loads(path.read_text())["session_id"] == f"session-{number}"
