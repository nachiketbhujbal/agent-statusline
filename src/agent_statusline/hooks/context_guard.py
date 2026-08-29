#!/usr/bin/env python3
"""UserPromptSubmit: warn when the context window is filling up.

Live token usage is read from the transcript's most recent assistant message,
so it is never stale. Only the window SIZE comes from the status-line payload
(it is a constant for the session); it falls back to 1M if unavailable.
"""
import json
import os
import sys
import time

if __package__ in (None, ""):  # running as a plain script
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    )

from agent_statusline.paths import state

WARN, CRIT = 80, 90


def window_size():
    try:
        with open(state("statusline-last-payload.json")) as fh:
            return int(json.load(fh)["context_window"]["context_window_size"])
    except Exception:
        return 1_000_000


def live_tokens(path):
    """Last assistant message's usage == current context occupancy."""
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
            u = json.loads(line)["message"]["usage"]
        except Exception:
            continue
        return sum(
            int(u.get(k) or 0)
            for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        )
    return 0


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    try:
        with open(state("hook-lastrun.json"), "w") as fh:
            json.dump(
                {
                    "hook": "UserPromptSubmit",
                    "at": time.time(),
                    "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "session": payload.get("session_id"),
                },
                fh,
            )
    except Exception:
        pass

    size = window_size()
    live = live_tokens(payload.get("transcript_path"))
    if not live or not size:
        return 0
    pct = live / size * 100
    if pct < WARN:
        return 0

    urgency = "CRITICAL" if pct >= CRIT else "WARNING"
    human = f"{urgency}: context window {pct:.0f}% full ({live:,} of {size:,} tokens)."
    print(
        json.dumps(
            {
                "systemMessage": human + " Consider a focused /compact.",
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        f"{human} Before continuing, offer the user a focused compaction: propose "
                        f"`/compact` with a summary instruction naming only what this task still "
                        f"needs (current decisions, open questions, active file paths, the "
                        f"immediate next step), and say explicitly what would be dropped. Do not "
                        f"compact without their approval, and do not repeat this offer if they "
                        f"have already declined it this session."
                    ),
                },
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
