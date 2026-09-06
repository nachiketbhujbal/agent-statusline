#!/usr/bin/env python3
"""Where runtime state lives.

Code lives in this repository; *state* does not. Ledger, caches and logs are
machine-local and must never be committed, so they stay in the agent's own
config directory (`~/.claude` by default). Override with AGENT_STATUSLINE_STATE
to run a second instance, or to point a test at a throwaway directory.
"""
import os
import stat

STATE_DIR = os.path.abspath(
    os.path.expanduser(os.environ.get("AGENT_STATUSLINE_STATE") or "~/.claude")
)


def _resolved_state_dir():
    """Return one verified state root, creating an absent root privately."""
    created = False
    try:
        os.mkdir(STATE_DIR, 0o700)
        created = True
    except FileExistsError:
        pass
    except FileNotFoundError:
        os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
        created = True

    directory = os.path.realpath(STATE_DIR)
    info = os.stat(directory)
    if not stat.S_ISDIR(info.st_mode):
        raise NotADirectoryError(f"unsafe agent-statusline state root: {STATE_DIR}")
    if created:
        os.chmod(directory, 0o700)
    return directory


def state(name):
    """Absolute path to one direct state entry in a once-resolved root."""
    if not isinstance(name, str) or not name or os.path.basename(name) != name:
        raise ValueError("state entry must be a direct non-empty filename")
    return os.path.join(_resolved_state_dir(), name)
