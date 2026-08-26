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
            # close_session only touches a row that exists; make sure one does, so a
            # session that ended before its first status-line render still gets sealed.
            data = ledger.load()
            if sid not in data["sessions"]:
                data["sessions"][sid] = {"cost": 0.0, "started": ledger.iso()}
                ledger.save(data)
            ledger.close_session(
                sid,
                payload.get("reason") or payload.get("source") or "end",
                transcript=payload.get("transcript_path"),
            )
        except Exception:
            pass
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
