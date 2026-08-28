"""Test setup.

The state directory is redirected BEFORE any package import, because
`paths.STATE_DIR` is resolved at import time. Nothing in the suite may touch the
real `~/.claude` -- exercising cost paths against a live ledger has corrupted
real spend figures before (docs/adrs/0014).
"""

import json
import os
import tempfile
from pathlib import Path

_STATE = tempfile.mkdtemp(prefix="agent-statusline-tests-")
os.environ["AGENT_STATUSLINE_STATE"] = _STATE

import pytest


@pytest.fixture
def payload():
    """A realistic Claude Code status-line payload."""
    fixture_dir = Path(__file__).parent / "fixtures"
    value = json.loads((fixture_dir / "statusline-payload.json").read_text())
    value["transcript_path"] = str(fixture_dir / "statusline-transcript.jsonl")
    return value
