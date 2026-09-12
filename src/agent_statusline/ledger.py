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
import datetime
import math
import os
import sys
from collections.abc import Mapping

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
    now = _observation_epoch(when)
    changed = False
    schema = data.get("cost_event_schema")
    if schema is None:
        if any(
            key in data for key in ("cost_event_schema", "cost_tracking_started", "cost_events")
        ):
            # Journal-shaped state without a recognized schema may contain
            # evidence we do not understand. Preserve it and fail closed rather
            # than erasing it to manufacture an apparently complete history.
            return False
        data["cost_event_schema"] = COST_EVENT_SCHEMA
        data["cost_tracking_started"] = iso(now)
        data["cost_events"] = []
        for session, row in data.get("sessions", {}).items():
            if isinstance(row, dict):
                # A seed marker has meaning only with its matching journal
                # schema. Ignore a stale marker from malformed/partial state.
                row.pop("cost_journal_seeded", None)
            changed = _seed_cost_row(data, session, row, now) or changed
        return True
    if schema != COST_EVENT_SCHEMA or not isinstance(data.get("cost_events"), list):
        return False

    events = data["cost_events"]
    cutoff = now - COST_EVENT_RETENTION_SECONDS
    valid_events = [event for event in events if _valid_cost_event(event)]
    tracking_started = epoch(data.get("cost_tracking_started"))
    journal_order_ok = 0 < tracking_started <= now and all(
        epoch(event["at"]) >= tracking_started for event in valid_events
    )
    if len(valid_events) == len(events) and journal_order_ok:
        retained = [event for event in valid_events if epoch(event["at"]) >= cutoff]
        if retained != events:
            data["cost_events"] = events = retained
            changed = True

    row = data.get("sessions", {}).get(sid, {})
    if not isinstance(row, Mapping) or not row.get("cost_journal_seeded"):
        return _seed_cost_row(data, sid, row, now) or changed

    previous = _finite_number(previous_cost)
    current = _finite_number(current_cost)
    if previous is None or previous < 0 or current is None or current < 0:
        return changed
    delta = current - previous
    if math.isfinite(delta) and delta > 1e-9:
        evidence = epoch(accrued_at)
        accrued = min(evidence, now) if evidence > 0 else now
        events.append(
            {
                "at": iso(now),
                "accrued_at": iso(accrued),
                "session": sid,
                "delta": delta,
                "lifetime": current,
                "seed": False,
            }
        )
        changed = True
    return changed


def rolling_costs(data, when=None):
    """Return exact sums or proven lower bounds for every displayed horizon."""
    now = _observation_epoch(when)
    result = {}
    schema_ok = data.get("cost_event_schema") == COST_EVENT_SCHEMA
    events = data.get("cost_events")
    events_ok = isinstance(events, list)
    event_rows = events if isinstance(events, list) else []
    valid_events = [
        event for event in event_rows if _valid_cost_event(event) and epoch(event["at"]) <= now
    ]
    if len(valid_events) != len(event_rows):
        events_ok = False
    tracking_started = epoch(data.get("cost_tracking_started"))
    tracking_ok = 0 < tracking_started <= now
    if tracking_ok and any(epoch(event["at"]) < tracking_started for event in valid_events):
        events_ok = False
    for key, seconds in COST_WINDOWS.items():
        cutoff = now - seconds
        amount = 0.0
        unattributed = 0.0
        open_sessions = set()
        complete = bool(schema_ok and events_ok and tracking_ok)
        if schema_ok:
            for event in valid_events:
                delta = float(event["delta"])
                accrued = epoch(event["accrued_at"])
                if not event["seed"]:
                    if accrued >= cutoff:
                        candidate = amount + delta
                        if math.isfinite(candidate):
                            amount = candidate
                        else:
                            complete = False
                    continue
                started = epoch(event.get("started_at"))
                if started >= cutoff:
                    candidate = amount + delta
                    if math.isfinite(candidate):
                        amount = candidate
                    else:
                        complete = False
                elif accrued >= cutoff:
                    candidate = unattributed + delta
                    if math.isfinite(candidate):
                        unattributed = candidate
                    else:
                        complete = False
                    open_sessions.add(event["session"])
                    complete = False
        result[key] = amount
        result[key + "_complete"] = complete
        result[key + "_unattributed"] = unattributed
        result[key + "_open_rows"] = len(open_sessions)
    return result


def _valid_cost_event(event):
    if not isinstance(event, Mapping):
        return False
    session = event.get("session")
    if not isinstance(session, str):
        return False
    observed = epoch(event.get("at"))
    accrued = epoch(event.get("accrued_at"))
    if observed <= 0 or accrued <= 0 or accrued > observed:
        return False
    if type(event.get("seed")) is not bool:
        return False
    delta_value = event.get("delta")
    lifetime_value = event.get("lifetime")
    if isinstance(delta_value, bool) or not isinstance(delta_value, (int, float)):
        return False
    if isinstance(lifetime_value, bool) or not isinstance(lifetime_value, (int, float)):
        return False
    delta = _finite_number(delta_value)
    lifetime = _finite_number(lifetime_value)
    if delta is None or delta < 0 or lifetime is None or lifetime < 0 or delta > lifetime + 1e-9:
        return False
    if event["seed"]:
        if "started_at" not in event:
            return False
        started = event.get("started_at")
        if started is not None:
            started_epoch = epoch(started)
            if started_epoch <= 0 or started_epoch > accrued:
                return False
    return True


def _seed_cost_row(data, sid, row, when):
    """Record a non-accrual baseline once for one session."""
    if not isinstance(sid, str) or not isinstance(row, dict):
        return False
    if row.get("cost_journal_seeded"):
        return False
    row["cost_journal_seeded"] = True
    amount = _finite_number(row.get("cost", 0.0))
    if amount is None or amount <= 1e-9:
        return True
    started = epoch(row.get("started"))
    if row.get("state") == "closed":
        through = max(epoch(row.get("closed")), epoch(row.get("updated")))
    else:
        through = epoch(row.get("updated"))
    through = min(through, when) if through > 0 else when
    if started <= 0 or started > through:
        started = 0.0
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


def _finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _observation_epoch(when):
    if when is None:
        return float(math.floor(datetime.datetime.now().astimezone().timestamp()))
    observed = epoch(when)
    if observed > 0:
        return float(math.floor(observed))
    return float(math.floor(datetime.datetime.now().astimezone().timestamp()))


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
    if value is None or isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else 0.0
    try:
        if isinstance(value, str) and value.endswith("Z"):
            value = value[:-1] + "+00:00"
        number = datetime.datetime.fromisoformat(value).timestamp()
        return number if math.isfinite(number) else 0.0
    except Exception:
        return 0.0


def _normalized_sessions(value):
    if not isinstance(value, Mapping):
        return {}
    return {sid: dict(row) for sid, row in value.items() if isinstance(row, Mapping)}


def load():
    data = read_json(LEDGER, {})
    data["sessions"] = _normalized_sessions(data.get("sessions"))
    return data


def save(data):
    """Atomic temp+rename, pretty-printed so the file stays readable by hand."""

    def replace(current):
        replacement = dict(data) if isinstance(data, Mapping) else {}
        replacement["sessions"] = _normalized_sessions(replacement.get("sessions"))
        current.clear()
        current.update(replacement)
        return True, None

    update_json(LEDGER, {}, replace)


def update(updater):
    """Run one locked ledger transaction with a normalized sessions mapping."""

    def normalized(data):
        previous = data.get("sessions")
        sessions = _normalized_sessions(previous)
        normalization_changed = "sessions" in data and previous != sessions
        data["sessions"] = sessions
        changed, result = updater(data)
        return normalization_changed or changed, result

    return update_json(LEDGER, {}, normalized)


def close_session(sid, reason="end", transcript=None, when=None, create=False):
    """Stamp a row closed. Returns the row, or None if the session is unknown."""

    def close(data):
        sessions = data["sessions"]
        row = sessions.get(sid)
        if not isinstance(row, Mapping):
            if not create:
                return False, None
            row = {"cost": 0.0, "started": iso(when)}
            sessions[sid] = row
        else:
            row = dict(row)
            sessions[sid] = row
        row["state"] = "closed"
        row["closed"] = iso(when)
        row["reason"] = reason
        if transcript:
            row["transcript"] = transcript
        return True, dict(row)

    return update(close)


def _main():
    import argparse

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
