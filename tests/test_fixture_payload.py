"""Hermetic evidence materialization shared by pytest and installed smoke."""

import datetime
import json
import os
from pathlib import Path

from agent_statusline import selftest
from fixture_payload import materialize_payload


def test_materialization_resolves_paths_and_dynamic_windows(tmp_path):
    now = 1_800_000_000.0
    workspace = tmp_path / "workspace"

    payload = materialize_payload(workspace, now=now)

    transcript = Path(payload["transcript_path"])
    assert transcript.is_absolute() and transcript.parent == workspace
    assert Path(payload["cwd"]) == workspace
    assert Path(payload["workspace"]["current_dir"]) == workspace
    assert payload["rate_limits"]["five_hour"]["resets_at"] == now + 4 * 3600
    assert payload["rate_limits"]["seven_day"]["resets_at"] == now + 5 * 86400
    expected_stamp = datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat()
    assert expected_stamp in transcript.read_text(encoding="utf-8")
    assert "__MATERIALIZED_" not in transcript.read_text(encoding="utf-8")


def test_test_process_home_is_disposable_and_has_no_live_claude_config():
    home = Path(os.environ["HOME"])
    assert home.name.startswith("agent-statusline-home-")
    assert not (home / ".claude.json").exists()


def test_runtime_selftest_matches_the_committed_synthetic_contract(tmp_path):
    now = 1_800_000_000.0
    workspace = (tmp_path / "workspace").resolve()
    committed = materialize_payload(workspace, now=now)
    committed_entries = [
        json.loads(line)
        for line in Path(committed["transcript_path"]).read_text(encoding="utf-8").splitlines()
    ]

    selftest._write_transcript(committed["transcript_path"], now)
    runtime = selftest._payload(str(workspace), committed["transcript_path"], now)
    runtime_entries = [
        json.loads(line)
        for line in Path(committed["transcript_path"]).read_text(encoding="utf-8").splitlines()
    ]

    assert runtime == committed
    assert runtime_entries == committed_entries
    assert tuple(selftest.ORDER) == selftest.EXPECTED_ROWS
