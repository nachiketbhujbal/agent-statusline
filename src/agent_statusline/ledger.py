#!/usr/bin/env python3
"""Shared cost-ledger helpers: ISO 8601 timestamps and session close stamping.

Timestamps in `cost-ledger.json` are ISO 8601 local time with a UTC offset,
e.g. `2026-08-24T00:48:13-07:00`. Legacy epoch floats are still accepted on
read so older rows keep working; anything written is ISO.

CLI — close a session that can never fire the SessionEnd hook (killed process,
crash, lost daemon):

    python3 <repo>/src/ledger.py close <session-id> --reason killed
    python3 <repo>/src/ledger.py show
"""
import argparse
import datetime
import json
import os
import sys

# Entry point: make the package importable when run as a plain script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from agent_statusline.paths import state

LEDGER = state("cost-ledger.json")

# Statuses written into a row's `reason`. Anything Claude Code reports via the
# SessionEnd payload passes through as-is; these are the ones we write ourselves.
REASONS = {
    "end": "session ended normally, hook fired",
    "clear": "conversation cleared",
    "logout": "user logged out",
    "other": "SessionEnd fired with an unclassified reason",
    "killed": "process terminated without SessionEnd; stamped out of band",
}

# A row's lifecycle. `closed` keeps the *last* close time even after a resume, so
# state is what says whether the session is running right now.
STATES = ("live", "closed")


def apply_cost(row, payload_cost, pid=None):
    """Fold the payload's `total_cost_usd` into a lifetime cost for the session.

    The payload reports cost for the current CLI run. Whether that number is
    cumulative across a `--resume` or restarts from zero is not documented
    anywhere we can rely on, so this handles both: a *decrease* means a new run
    began, and the finished run's total is banked into `cost_base`. If the value
    turns out to be cumulative it simply never decreases, `cost_base` stays 0,
    and this reduces to using the payload directly.

        cost = cost_base (finished runs) + cost_run (this run)

    Also maintains `runs`. Returns the lifetime cost.
    """
    if payload_cost is None:
        return row.get("cost", 0.0)
    prev_run = row.get("cost_run")
    prev_pid = row.get("pid")
    base = row.get("cost_base", 0.0)
    if pid:
        row["pid"] = pid
    # A new run means the CLI process restarted, so a *changed pid* is the reliable
    # signal. A cost decrease alone is not: replaying a stale payload looks identical
    # to a resume and would wrongly bank the run. Decrease is only used as a fallback
    # when the pid is unknown, and then only alongside it.
    new_run = False
    if prev_run is None:
        new_run = True
    elif prev_pid and pid:
        new_run = (pid != prev_pid) and payload_cost < prev_run - 1e-9
    elif payload_cost < prev_run - 1e-9:
        new_run = True
    if prev_run is None:
        # First sighting, or a row written before this schema existed. Any cost
        # already on the row that the payload does not account for is banked.
        base = max(0.0, float(row.get("cost", 0.0)) - payload_cost)
        row["runs"] = row.get("runs", 0) + 1
    elif new_run:
        base += prev_run
        row["runs"] = row.get("runs", 1) + 1
    elif payload_cost < prev_run - 1e-9:
        # Same process reporting less than before: a stale or replayed payload.
        # Keep the high-water mark rather than losing money to it.
        return row.get("cost", base + prev_run)
    row["cost_base"] = base
    row["cost_run"] = payload_cost
    row["cost"] = base + payload_cost
    return row["cost"]


def iso(when=None):
    """ISO 8601 local time with offset, to the second."""
    if when is None:
        dt = datetime.datetime.now().astimezone()
    elif isinstance(when, (int, float)):
        dt = datetime.datetime.fromtimestamp(when).astimezone()
    else:
        return when
    return dt.replace(microsecond=0).isoformat()


def epoch(value):
    """Epoch seconds from an ISO string or a legacy numeric stamp. 0 if unparseable."""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return datetime.datetime.fromisoformat(value).timestamp()
    except Exception:
        return 0.0


def load():
    try:
        with open(LEDGER) as fh:
            data = json.load(fh)
    except Exception:
        data = {}
    data.setdefault("sessions", {})
    return data


def save(data):
    """Atomic temp+rename, pretty-printed so the file stays readable by hand."""
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, LEDGER)


def close_session(sid, reason="end", transcript=None, when=None):
    """Stamp a row closed. Returns the row, or None if the session is unknown."""
    data = load()
    row = data["sessions"].get(sid)
    if row is None:
        return None
    row["state"] = "closed"
    row["closed"] = iso(when)
    row["reason"] = reason
    if transcript:
        row["transcript"] = transcript
    save(data)
    return row


def _main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("close", help="stamp a session closed out of band")
    c.add_argument("session_id")
    c.add_argument("--reason", default="killed", choices=sorted(REASONS))
    c.add_argument("--at", help="ISO 8601 time (default: now)")
    sub.add_parser("show", help="print the ledger as a table")
    a = ap.parse_args()

    if a.cmd == "close":
        when = epoch(a.at) if a.at else None
        row = close_session(a.session_id, a.reason, when=when)
        if row is None:
            print(f"no such session: {a.session_id}", file=sys.stderr)
            return 1
        print(f"{a.session_id}  closed={row['closed']}  reason={row['reason']}")
        return 0

    rows = load()["sessions"]
    w = max((len(k) for k in rows), default=10)
    for sid, r in sorted(rows.items(), key=lambda kv: epoch(kv[1].get("started"))):
        runs = r.get("runs", "-")
        print(
            f"{sid:<{w}}  {str(r.get('state','-')):<6}  ${r.get('cost',0):>9.4f}"
            f"  (base ${r.get('cost_base',0):>8.4f} + run ${r.get('cost_run',0):>8.4f})"
            f"  runs={runs}  started={r.get('started','-')}"
            f"  updated={r.get('updated','-')}  closed={r.get('closed','-')}"
            f"  reason={r.get('reason','-')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
