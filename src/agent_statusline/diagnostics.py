"""Privacy-safe diagnostic evidence for failures hidden by the host."""

import datetime
import json

from agent_statusline.paths import state
from agent_statusline.storage import write_text

LAST_RENDER_ERROR = state("statusline-last-error.json")
ERROR_SCHEMA = 1


def record_render_failure(error):
    """Record only non-sensitive failure metadata.

    Exception messages and tracebacks can contain payload values, transcript
    paths, commands, or file contents. The breadcrumb deliberately excludes
    all of them.
    """
    record = {
        "schema": ERROR_SCHEMA,
        "occurred_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "phase": "render",
        "error_type": type(error).__name__,
    }
    write_text(LAST_RENDER_ERROR, json.dumps(record, sort_keys=True) + "\n")
