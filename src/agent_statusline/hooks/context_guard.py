#!/usr/bin/env python3
"""Warn at a configurable context threshold on Stop or prompt submission."""
import json
import math
import os
import sys
import time

if __package__ in (None, ""):  # running as a plain script
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    )

from agent_statusline.paths import state
from agent_statusline.session_metrics import read_snapshot
from agent_statusline.storage import read_json, write_text

DEFAULT_WARN = 80.0
CRIT = 90.0
THRESHOLD_ENV = "AGENT_STATUSLINE_CONTEXT_WARN_PCT"
MESSAGE_ENV = "AGENT_STATUSLINE_CONTEXT_WARN_MESSAGE"
EVENT_ENV = "AGENT_STATUSLINE_CONTEXT_WARN_EVENT"
VALID_EVENTS = {"stop", "submit", "both"}


def configuration(environ=None):
    """Return validated context-guard settings and an optional error."""
    source = os.environ if environ is None else environ
    raw_threshold = source.get(THRESHOLD_ENV, str(DEFAULT_WARN))
    try:
        threshold = float(raw_threshold)
    except (TypeError, ValueError):
        return None, f"{THRESHOLD_ENV} must be a number from 1 through 100"
    if not math.isfinite(threshold) or not 1 <= threshold <= 100:
        return None, f"{THRESHOLD_ENV} must be a number from 1 through 100"

    event = str(source.get(EVENT_ENV, "stop")).strip().lower()
    if event not in VALID_EVENTS:
        return None, f"{EVENT_ENV} must be stop, submit, or both"

    message = source.get(MESSAGE_ENV)
    if message is not None:
        message = str(message)
        if not message.strip() or "{pct}" not in message:
            return None, f"{MESSAGE_ENV} must be non-empty and contain {{pct}}"

    return {"threshold": threshold, "event": event, "message": message}, None


def window_size():
    try:
        payload = read_json(state("statusline-last-payload.json"), {})
        return int(payload["context_window"]["context_window_size"])
    except Exception:
        return 1_000_000


def live_tokens(path):
    """Return current occupancy from the last assistant transcript message."""
    if not path or not os.path.exists(path):
        return 0
    try:
        with open(path, "rb") as fh:
            size = os.fstat(fh.fileno()).st_size
            fh.seek(max(0, size - 400_000))
            lines = fh.read().split(b"\n")
    except Exception:
        return 0
    for line in reversed(lines):
        if b'"assistant"' not in line:
            continue
        try:
            usage = json.loads(line)["message"]["usage"]
        except Exception:
            continue
        return sum(
            int(usage.get(key) or 0)
            for key in (
                "input_tokens",
                "cache_creation_input_tokens",
                "cache_read_input_tokens",
            )
        )
    return 0


def context_usage(payload):
    """Prefer the public session snapshot, then use the legacy live fallback."""
    session_id = payload.get("session_id")
    try:
        snapshot = read_snapshot(session_id) if session_id else None
    except Exception:
        snapshot = None
    if snapshot:
        try:
            pct = float(snapshot["context_used_pct"])
            if math.isfinite(pct) and pct >= 0:
                size = int(snapshot.get("context_window_size") or 0)
                live = round(pct / 100 * size) if size > 0 else 0
                return pct, live, size
        except (TypeError, ValueError, OverflowError, KeyError):
            pass

    size = window_size()
    live = live_tokens(payload.get("transcript_path"))
    if not live or not size:
        return None
    return live / size * 100, live, size


def _event(payload):
    name = payload.get("hook_event_name")
    if name == "Stop":
        return "stop", "Stop"
    return "submit", "UserPromptSubmit"


def _messages(pct, live, size, custom):
    urgency = "CRITICAL" if pct >= CRIT else "WARNING"
    human = f"{urgency}: context window {pct:.0f}% full"
    if live and size:
        human += f" ({live:,} of {size:,} tokens)"
    human += "."
    if custom is not None:
        rendered = custom.replace("{pct}", f"{pct:.0f}")
        return rendered, rendered
    return (
        human + " Consider a focused /compact.",
        (
            f"{human} Before continuing, offer the user a focused compaction: propose "
            f"`/compact` with a summary instruction naming only what this task still "
            f"needs (current decisions, open questions, active file paths, the "
            f"immediate next step), and say explicitly what would be dropped. Do not "
            f"compact without their approval, and do not repeat this offer if they "
            f"have already declined it this session."
        ),
    )


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    selected, event_name = _event(payload)
    try:
        write_text(
            state("hook-lastrun.json"),
            json.dumps(
                {
                    "hook": event_name,
                    "at": time.time(),
                    "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "session": payload.get("session_id"),
                }
            ),
        )
    except Exception:
        pass

    config, error = configuration()
    if error:
        print(json.dumps({"systemMessage": f"agent-statusline: {error}"}))
        return 0
    if config["event"] not in (selected, "both"):
        return 0

    usage = context_usage(payload)
    if usage is None:
        return 0
    pct, live, size = usage
    if pct < config["threshold"]:
        return 0

    system_message, model_message = _messages(pct, live, size, config["message"])
    output = {"systemMessage": system_message}
    if selected == "submit":
        output["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": model_message,
        }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
