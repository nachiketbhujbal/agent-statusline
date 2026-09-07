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


class _StateEntry(os.PathLike):
    """A package state entry whose root is initialized on first filesystem use."""

    def __init__(self, name):
        self.name = name
        self._path = None

    def __fspath__(self):
        if self._path is None:
            self._path = os.path.join(_resolved_state_dir(), self.name)
        return self._path

    def __str__(self):
        return os.fspath(self)


def state(name):
    """A lazy path to one direct state entry inside the verified state root."""
    if not isinstance(name, str) or name in ("", ".", "..") or os.path.basename(name) != name:
        raise ValueError("state entry must be a direct non-empty filename")
    return _StateEntry(name)
