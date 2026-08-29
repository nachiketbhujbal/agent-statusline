#!/usr/bin/env python3
"""Where runtime state lives.

Code lives in this repository; *state* does not. Ledger, caches and logs are
machine-local and must never be committed, so they stay in the agent's own
config directory (`~/.claude` by default). Override with AGENT_STATUSLINE_STATE
to run a second instance, or to point a test at a throwaway directory.
"""
import os

STATE_DIR = os.path.abspath(
    os.path.expanduser(os.environ.get("AGENT_STATUSLINE_STATE") or "~/.claude")
)


def state(name):
    """Absolute path to a state file, creating the directory if needed."""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
    except Exception:
        pass
    return os.path.join(STATE_DIR, name)
