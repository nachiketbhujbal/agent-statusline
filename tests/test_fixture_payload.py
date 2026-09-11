"""Hermetic evidence materialization shared by pytest and installed smoke."""

import datetime
import json
import os
from pathlib import Path

import pytest

from agent_statusline import selftest
from fixture_payload import (
    PAYLOAD_TEMPLATE,
    TRANSCRIPT_EVIDENCE,
    TRANSCRIPT_TEMPLATE,
    materialize_payload,
    verify_render_contract,
)


def test_templates_use_materialized_paths_and_not_fixed_temporary_paths():
    payload_text = PAYLOAD_TEMPLATE.read_text(encoding="utf-8")
    transcript_text = TRANSCRIPT_TEMPLATE.read_text(encoding="utf-8")

    assert "__MATERIALIZED_TRANSCRIPT__" in payload_text
    assert "__MATERIALIZED_WORKSPACE__" in payload_text
    assert "__MATERIALIZED_NOW__" in transcript_text
    assert "__WORKSPACE__/" in transcript_text
    assert '"/tmp' not in payload_text + transcript_text


def test_materialization_resolves_paths_and_dynamic_windows(tmp_path):
    now = 1_800_000_000.0
    workspace = tmp_path / "workspace"

    payload = materialize_payload(workspace, now=now)

    transcript = Path(payload["transcript_path"])
    transcript_text = transcript.read_text(encoding="utf-8")
    assert transcript.is_absolute() and transcript.parent == workspace
    assert Path(payload["cwd"]) == workspace
    assert Path(payload["workspace"]["current_dir"]) == workspace
    assert Path(payload["workspace"]["project_dir"]) == workspace
    assert payload["rate_limits"]["five_hour"]["resets_at"] == now + 4 * 3600
    assert payload["rate_limits"]["seven_day"]["resets_at"] == now + 5 * 86400
    expected_stamp = datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat()
    assert expected_stamp in transcript_text
    assert str(workspace / "README.md") in transcript_text
    assert str(workspace / "example.py") in transcript_text
    assert "__MATERIALIZED_" not in json.dumps(payload)
    assert "__MATERIALIZED_" not in transcript_text
    assert "__WORKSPACE__" not in transcript_text


def test_test_process_home_is_disposable_and_has_no_live_claude_config():
    home = Path(os.environ["HOME"])
    assert home.name.startswith("agent-statusline-home-")
    assert not (home / ".claude.json").exists()


def test_render_contract_rejects_an_empty_or_partial_smoke():
    with pytest.raises(AssertionError):
        verify_render_contract("", ["PROJECT", "MODEL"])
    with pytest.raises(AssertionError):
        verify_render_contract("PROJECT project\nMODEL model\n", ["PROJECT", "MODEL"])


def test_runtime_selftest_matches_the_committed_synthetic_contract(tmp_path):
    now = 1_800_000_000.0
    workspace = (tmp_path / "workspace").resolve()
    committed = materialize_payload(workspace, now=now)
    committed_entries = [
        json.loads(line)
        for line in Path(committed["transcript_path"]).read_text(encoding="utf-8").splitlines()
    ]

    runtime = selftest._materialize_payload(str(workspace), now)
    runtime_entries = [
        json.loads(line)
        for line in Path(runtime["transcript_path"]).read_text(encoding="utf-8").splitlines()
    ]

    assert runtime == committed
    assert runtime_entries == committed_entries
    assert tuple(selftest.ORDER) == selftest.EXPECTED_ROWS
    assert selftest.TRANSCRIPT_EVIDENCE == TRANSCRIPT_EVIDENCE
