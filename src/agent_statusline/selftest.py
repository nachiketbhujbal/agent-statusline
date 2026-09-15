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

from agent_statusline.session_metrics import SCHEMA_VERSION, filename_for
from agent_statusline.statusline import ORDER

EXPECTED_ROWS = tuple(ORDER)
ANSI = re.compile(r"\x1b\[[0-9;]*m")
TRANSCRIPT_EVIDENCE = {
    "CACHE": ("1h ttl", "writes 200 1h"),
    "TOKENS": ("total 2k reused", "200 written", "20 uncached"),
    "TOOLS": ("2 calls", "Read1", "Edit1"),
    "TIMING": ("turn 1s last", "hooks 1 runs", "12ms median"),
}


def _write_transcript(path, workspace, now):
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
                        "input": {"file_path": os.path.join(workspace, "README.md")},
                    },
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": os.path.join(workspace, "example.py")},
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
            handle.write(json.dumps(entry, separators=(",", ":")) + "\n")


def _materialize_payload(workspace, now):
    transcript = os.path.join(workspace, "statusline-transcript.jsonl")
    _write_transcript(transcript, workspace, now)
    return {
        "session_id": "synthetic-session-0001",
        "session_name": "Synthetic smoke session",
        "transcript_path": transcript,
        "cwd": workspace,
        "version": "2.1.246",
        "effort": {"level": "high"},
        "model": {"id": "claude-opus-synthetic", "display_name": "Synthetic Opus"},
        "workspace": {"current_dir": workspace, "project_dir": workspace, "added_dirs": []},
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


def _rendered_rows(output):
    labels = []
    rows = {}
    current = None
    for physical in (ANSI.sub("", line) for line in output.splitlines()):
        if not physical.strip():
            continue
        if not physical.startswith(" "):
            current, _, content = physical.partition(" ")
            labels.append(current)
            rows[current] = content.strip()
        elif current is not None:
            rows[current] += " " + physical.strip()
    return tuple(labels), rows


def _has_transcript_evidence(rows):
    return all(
        marker in rows.get(label, "")
        for label, markers in TRANSCRIPT_EVIDENCE.items()
        for marker in markers
    )


def _private_directory(path):
    try:
        info = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700


def _private_state(state_dir):
    if not _private_directory(state_dir):
        return False
    for directory, directories, files in os.walk(state_dir):
        if not _private_directory(directory):
            return False
        for name in directories:
            if not _private_directory(os.path.join(directory, name)):
                return False
        for name in files:
            try:
                info = os.lstat(os.path.join(directory, name))
            except OSError:
                return False
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                return False
    return True


def _fail(reason):
    print(f"selftest failed: {reason}", file=sys.stderr)
    return 1


def _valid_metrics(state_dir, payload):
    path = os.path.join(state_dir, filename_for(payload["session_id"]))
    try:
        with open(path, encoding="utf-8") as handle:
            snapshot = json.load(handle)
    except (OSError, ValueError):
        return False
    expected = {
        "schema_version": SCHEMA_VERSION,
        "producer": "agent-statusline",
        "session_id": payload["session_id"],
        "host": "claude",
        "model": payload["model"]["display_name"],
        "context_used_pct": payload["context_window"]["used_percentage"],
        "context_window_size": payload["context_window"]["context_window_size"],
        "cost_usd": payload["cost"]["total_cost_usd"],
        "turns": 1,
        "lines_added": payload["cost"]["total_lines_added"],
        "lines_removed": payload["cost"]["total_lines_removed"],
        "session_title": payload["session_name"],
    }
    return (
        all(snapshot.get(key) == value for key, value in expected.items())
        and isinstance(snapshot.get("producer_version"), str)
        and isinstance(snapshot.get("started_at"), str)
        and isinstance(snapshot.get("updated_at"), str)
    )


def run():
    """Render a full synthetic payload in a fresh process and private state."""
    with tempfile.TemporaryDirectory(prefix="agent-statusline-selftest-") as root:
        workspace = os.path.abspath(root)
        now = time.time()
        state_dir = os.path.join(workspace, "state")
        home_dir = os.path.join(workspace, "home")
        os.mkdir(home_dir, mode=0o700)
        payload = _materialize_payload(workspace, now)
        env = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("COV_CORE_") and key != "COVERAGE_PROCESS_START"
        }
        env["HOME"] = home_dir
        env["CLAUDE_CONFIG_DIR"] = os.path.join(home_dir, ".claude")
        env["AGENT_STATUSLINE_STATE"] = state_dir
        env["COLUMNS"] = "240"
        env["PYTHONPATH"] = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        try:
            process = subprocess.run(
                [sys.executable, "-m", "agent_statusline"],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=20,
                env=env,
                cwd=workspace,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return _fail("isolated renderer timed out")
        if process.returncode:
            return _fail("isolated renderer exited non-zero")
        labels, rows = _rendered_rows(process.stdout)
        if labels != EXPECTED_ROWS:
            return _fail("isolated renderer did not emit all approved rows in order")
        if not _has_transcript_evidence(rows):
            return _fail("isolated renderer did not emit the approved transcript evidence")
        if not _valid_metrics(state_dir, payload):
            return _fail("isolated renderer did not publish the documented session metrics")
        if not _private_directory(home_dir):
            return _fail("isolated home is missing or not private")
        if not _private_state(state_dir):
            return _fail("isolated runtime state is missing or not private")
    count = len(EXPECTED_ROWS)
    print(f"selftest ok: isolated renderer emitted all {count} approved rows with private state")
    return 0
