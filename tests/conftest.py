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

from fixture_payload import materialize_payload  # noqa: E402


@pytest.fixture
def payload(tmp_path):
    """A realistic Claude Code status-line payload."""
    return materialize_payload(tmp_path / "synthetic-workspace")
