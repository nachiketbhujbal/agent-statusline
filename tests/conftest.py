"""Test setup.

The state directory is redirected BEFORE any package import, because
`paths.STATE_DIR` is resolved at import time. Nothing in the suite may touch the
real `~/.claude` -- exercising cost paths against a live ledger has corrupted
real spend figures before (docs/adrs/0014).
"""

import os
import tempfile

# HOME too, not just the state dir: the installer reads ~/.claude.json for the
# native-timestamp feature flag, so a suite that leaves HOME alone passes or
# fails depending on a live flag on the developer's machine.
_HOME = tempfile.mkdtemp(prefix="agent-statusline-home-")
_STATE = tempfile.mkdtemp(prefix="agent-statusline-tests-")
os.environ["HOME"] = _HOME
os.environ["AGENT_STATUSLINE_STATE"] = _STATE

import pytest  # noqa: E402


@pytest.fixture
def payload():
    """A realistic Claude Code status-line payload."""
    return {
        "session_id": "test-session-0001",
        "session_name": "A test session",
        "transcript_path": "/nonexistent/transcript.jsonl",
        "cwd": "/tmp/project",
        "version": "2.1.246",
        "effort": {"level": "high"},
        "model": {"id": "claude-opus-5", "display_name": "Opus 5"},
        "workspace": {
            "current_dir": "/tmp/project",
            "project_dir": "/tmp/project",
            "added_dirs": [],
        },
        "output_style": {"name": "default"},
        "thinking": {"enabled": True},
        "fast_mode": False,
        "cost": {
            "total_cost_usd": 1.25,
            "total_duration_ms": 600000,
            "total_api_duration_ms": 120000,
            "total_lines_added": 10,
            "total_lines_removed": 2,
        },
        "context_window": {
            "context_window_size": 1000000,
            "used_percentage": 14,
            "current_usage": {
                "input_tokens": 2,
                "output_tokens": 800,
                "cache_creation_input_tokens": 700,
                "cache_read_input_tokens": 70000,
            },
        },
        "rate_limits": {
            "five_hour": {"used_percentage": 15, "resets_at": 4102444800},
            "seven_day": {"used_percentage": 49, "resets_at": 4102444800},
        },
    }
