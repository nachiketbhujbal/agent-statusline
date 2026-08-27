#!/usr/bin/env python3
"""SessionEnd: finalize this session's entry in the cost ledger.

Marks the row `state: closed` and stamps an ISO 8601 `closed` time and a
`reason`, through `ledger.close_session` so the lifecycle is defined in one
place. Sessions that never reach this hook -- a killed process, a lost daemon --
are stamped out of band with `agent-statusline ledger close <id> --reason killed`.
"""
import json
import os
import sys

if __package__ in (None, ""):  # running as a plain script
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.realpath(__file__)))))

from agent_statusline import ledger


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except Exception:
        payload = {}

    sid = payload.get("session_id")
    if sid:
        try:
            ledger.close_session(
                sid,
                payload.get("reason") or payload.get("source") or "end",
                transcript=payload.get("transcript_path"),
                create=True,
            )
        except Exception:
            pass
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
