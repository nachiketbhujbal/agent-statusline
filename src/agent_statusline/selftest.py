"""An isolated installed-renderer health check."""

import datetime
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time

from agent_statusline.statusline import ORDER

EXPECTED_ROWS = tuple(ORDER)
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _write_transcript(path, now):
    entries = [
        {
            "type": "user",
            "uuid": "synthetic-root-0001",
            "permissionMode": "plan",
            "message": {"content": "Synthetic prompt"},
        },
        {
            "type": "assistant",
            "timestamp": datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat(),
            "message": {
                "model": "claude-opus-synthetic",
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Read",
                        "input": {"file_path": "/synthetic/project/README.md"},
                    },
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "/synthetic/project/example.py"},
                    },
                ],
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 80,
                    "cache_creation_input_tokens": 200,
                    "cache_read_input_tokens": 2000,
                    "output_tokens_details": {"thinking_tokens": 25},
                    "cache_creation": {"ephemeral_1h_input_tokens": 200},
                    "service_tier": "standard",
                },
            },
        },
        {"type": "user", "message": {"content": [{"type": "tool_result", "is_error": False}]}},
        {"type": "system", "subtype": "turn_duration", "durationMs": 1234},
        {
            "type": "system",
            "subtype": "stop_hook_summary",
            "hookInfos": [{"durationMs": 12}],
            "hookErrors": [],
        },
    ]
    with open(path, "w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry) + "\n")


def _payload(root, transcript, now):
    return {
        "session_id": "synthetic-session-0001",
        "session_name": "Synthetic smoke session",
        "transcript_path": transcript,
        "cwd": root,
        "version": "2.1.246",
        "effort": {"level": "high"},
        "model": {"id": "claude-opus-synthetic", "display_name": "Synthetic Opus"},
        "workspace": {"current_dir": root, "project_dir": root, "added_dirs": []},
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
            "five_hour": {"used_percentage": 15, "resets_at": now + 4 * 3600},
            "seven_day": {"used_percentage": 49, "resets_at": now + 5 * 86400},
        },
    }


def _labels(output):
    lines = [ANSI.sub("", line) for line in output.splitlines()]
    return tuple(line.split()[0] for line in lines if line.strip() and not line.startswith(" "))


def _private_state(state_dir):
    if (
        os.path.islink(state_dir)
        or not os.path.isdir(state_dir)
        or stat.S_IMODE(os.stat(state_dir).st_mode) != 0o700
    ):
        return False
    for directory, directories, files in os.walk(state_dir):
        if os.path.islink(directory) or stat.S_IMODE(os.stat(directory).st_mode) != 0o700:
            return False
        for name in directories:
            path = os.path.join(directory, name)
            if os.path.islink(path) or stat.S_IMODE(os.stat(path).st_mode) != 0o700:
                return False
        for name in files:
            path = os.path.join(directory, name)
            if os.path.islink(path) or stat.S_IMODE(os.stat(path).st_mode) != 0o600:
                return False
    return True


def _fail(reason):
    print(f"selftest failed: {reason}", file=sys.stderr)
    return 1


def run():
    """Render a full synthetic payload in a fresh process and state directory."""
    with tempfile.TemporaryDirectory(prefix="agent-statusline-selftest-") as root:
        now = time.time()
        transcript = os.path.join(root, "transcript.jsonl")
        state_dir = os.path.join(root, "state")
        home_dir = os.path.join(root, "home")
        os.mkdir(home_dir, mode=0o700)
        _write_transcript(transcript, now)
        env = dict(os.environ)
        env["HOME"] = home_dir
        env["AGENT_STATUSLINE_STATE"] = state_dir
        env["COLUMNS"] = "200"
        try:
            process = subprocess.run(
                [sys.executable, "-m", "agent_statusline"],
                input=json.dumps(_payload(root, transcript, now)),
                capture_output=True,
                text=True,
                timeout=20,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return _fail("isolated renderer timed out")
        if process.returncode:
            return _fail("isolated renderer exited non-zero")
        if _labels(process.stdout) != EXPECTED_ROWS:
            return _fail("isolated renderer did not emit all approved rows in order")
        if not _private_state(state_dir):
            return _fail("isolated runtime state is missing or not private")
    print("selftest ok: isolated renderer emitted all 10 approved rows with private state")
    return 0
