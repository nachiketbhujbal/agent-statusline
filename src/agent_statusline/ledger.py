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
import math
import os
import sys

# Entry point: make the package importable when run as a plain script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from agent_statusline.paths import state
from agent_statusline.storage import read_json, update_json

LEDGER = state("cost-ledger.json")
COST_EVENT_SCHEMA = 1
COST_EVENT_RETENTION_SECONDS = 35 * 86400
COST_WINDOWS = {"d1": 86400, "d7": 7 * 86400, "d30": 30 * 86400}

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


def record_cost_delta(data, sid, previous_cost, current_cost, when=None, accrued_at=None):
    """Seed or append one positive lifetime-cost delta."""
    now = datetime.datetime.now().astimezone().timestamp() if when is None else float(when)
    changed = False
    schema = data.get("cost_event_schema")
    if schema is None:
        data["cost_event_schema"] = COST_EVENT_SCHEMA
        data["cost_tracking_started"] = iso(now)
        data["cost_events"] = []
        for session, row in data.get("sessions", {}).items():
            changed = _seed_cost_row(data, session, row, now) or changed
        return True
    if schema != COST_EVENT_SCHEMA or not isinstance(data.get("cost_events"), list):
        return False

    events = data["cost_events"]
    cutoff = now - COST_EVENT_RETENTION_SECONDS
    valid_events = [event for event in events if _valid_cost_event(event)]
    if len(valid_events) == len(events):
        retained = [event for event in valid_events if epoch(event["at"]) >= cutoff]
        if retained != events:
            data["cost_events"] = events = retained
            changed = True

    row = data.get("sessions", {}).get(sid, {})
    if not row.get("cost_journal_seeded"):
        return _seed_cost_row(data, sid, row, now) or changed

    delta = float(current_cost) - float(previous_cost)
    if math.isfinite(delta) and delta > 1e-9:
        # Transcript clocks are evidence, not authority over wall time. A bad
        # host clock or synthetic transcript must not keep an event inside every
        # rolling window by placing its accrual in the future.
        accrued = min(epoch(accrued_at) or now, now)
        events.append(
            {
                "at": iso(now),
                "accrued_at": iso(accrued),
                "session": sid,
                "delta": delta,
                "lifetime": float(current_cost),
                "seed": False,
            }
        )
        changed = True
    return changed


def rolling_costs(data, when=None):
    """Return exact sums or proven lower bounds for every displayed horizon."""
    now = datetime.datetime.now().astimezone().timestamp() if when is None else float(when)
    result = {}
    schema_ok = data.get("cost_event_schema") == COST_EVENT_SCHEMA
    events = data.get("cost_events")
    events_ok = isinstance(events, list)
    valid_events = [event for event in events or [] if _valid_cost_event(event)]
    if len(valid_events) != len(events or []):
        events_ok = False
    tracking_started = epoch(data.get("cost_tracking_started"))
    for key, seconds in COST_WINDOWS.items():
        cutoff = now - seconds
        amount = 0.0
        unattributed = 0.0
        open_sessions = set()
        exact = bool(schema_ok and events_ok and tracking_started)
        for event in valid_events:
            delta = float(event["delta"])
            if not event["seed"]:
                if epoch(event["accrued_at"]) >= cutoff:
                    amount += delta
                continue
            started = epoch(event.get("started_at"))
            through = epoch(event["accrued_at"])
            if started >= cutoff:
                amount += delta
            elif through >= cutoff:
                unattributed += delta
                open_sessions.add(event["session"])
                exact = False
        result[key] = amount
        result[key + "_complete"] = exact
        result[key + "_unattributed"] = unattributed
        result[key + "_open_rows"] = len(open_sessions)
    return result


def _valid_cost_event(event):
    if not isinstance(event, dict) or not isinstance(event.get("session"), str):
        return False
    if epoch(event.get("at")) <= 0 or epoch(event.get("accrued_at")) <= 0:
        return False
    if event.get("seed") not in (True, False):
        return False
    if event["seed"] and event.get("started_at") is not None and epoch(event["started_at"]) <= 0:
        return False
    delta = event.get("delta")
    return isinstance(delta, (int, float)) and math.isfinite(delta) and delta >= 0


def _seed_cost_row(data, sid, row, when):
    """Record a non-accrual baseline once for one session."""
    if not isinstance(row, dict) or row.get("cost_journal_seeded"):
        return False
    row["cost_journal_seeded"] = True
    amount = float(row.get("cost", 0.0))
    if not math.isfinite(amount) or amount <= 1e-9:
        return True
    started = epoch(row.get("started"))
    through = epoch(row.get("updated")) or when
    data["cost_events"].append(
        {
            "at": iso(when),
            "accrued_at": iso(through),
            "started_at": iso(started) if started else None,
            "session": sid,
            "delta": amount,
            "lifetime": amount,
            "seed": True,
        }
    )
    return True


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
    data = read_json(LEDGER, {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("sessions", {})
    return data


def save(data):
    """Atomic temp+rename, pretty-printed so the file stays readable by hand."""

    def replace(current):
        current.clear()
        current.update(data)
        current.setdefault("sessions", {})
        return True, None

    update_json(LEDGER, {}, replace)


def update(updater):
    """Run one locked ledger transaction."""

    def normalized(data):
        if not isinstance(data, dict):
            data = {}
        data.setdefault("sessions", {})
        return updater(data)

    return update_json(LEDGER, {}, normalized)


def close_session(sid, reason="end", transcript=None, when=None, create=False):
    """Stamp a row closed. Returns the row, or None if the session is unknown."""

    def close(data):
        row = data["sessions"].get(sid)
        if row is None:
            if not create:
                return False, None
            row = {"cost": 0.0, "started": iso(when)}
            data["sessions"][sid] = row
        row["state"] = "closed"
        row["closed"] = iso(when)
        row["reason"] = reason
        if transcript:
            row["transcript"] = transcript
        return True, dict(row)

    return update(close)


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
            f"{sid:<{w}}  {r.get('state','-')!s:<6}  ${r.get('cost',0):>9.4f}"
            f"  (base ${r.get('cost_base',0):>8.4f} + run ${r.get('cost_run',0):>8.4f})"
            f"  runs={runs}  started={r.get('started','-')}"
            f"  updated={r.get('updated','-')}  closed={r.get('closed','-')}"
            f"  reason={r.get('reason','-')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
