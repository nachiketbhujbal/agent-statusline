"""Documented per-session snapshots for local integrations."""

import hashlib
import json
import os
import sys
import time
from collections.abc import Mapping

from agent_statusline import __version__, ledger
from agent_statusline.coerce import finite_integer, finite_number
from agent_statusline.paths import state
from agent_statusline.storage import read_json, remove_json_if, update_json

SCHEMA_VERSION = 1
RETENTION_SECONDS = 35 * 24 * 60 * 60
PRUNE_INTERVAL_SECONDS = 60 * 60
MAX_SESSION_FILES = 512
FILE_PREFIX = "session-metrics-v1-"
FILE_SUFFIX = ".json"
OPT_OUT_ENV = "AGENT_STATUSLINE_SESSION_METRICS"


def enabled(environ=None):
    """Return whether render-time snapshot publication is enabled."""
    source = os.environ if environ is None else environ
    return str(source.get(OPT_OUT_ENV, "1")).strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def filename_for(session_id):
    """Return the bounded opaque filename for one host session identifier."""
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
    return f"{FILE_PREFIX}{digest}{FILE_SUFFIX}"


def path_for(session_id):
    return state(filename_for(session_id))


def _snapshot(facts, aggregate, now):
    identity = facts.get("identity", {})
    session_id = identity.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return None

    model = facts.get("model", {})
    context = facts.get("context", {})
    activity = facts.get("activity", {})
    money = facts.get("money", {})

    def optional_number(source, key, coerce):
        value = source.get(key)
        return None if value is None else coerce(value)

    row = {
        "schema_version": SCHEMA_VERSION,
        "producer": "agent-statusline",
        "producer_version": __version__,
        "session_id": session_id,
        "host": facts.get("host"),
        "model": model.get("display_name") or model.get("id"),
        "context_used_pct": optional_number(context, "used_percentage", finite_number),
        "context_window_size": optional_number(context, "window_size", finite_integer),
        "turns": (
            optional_number(activity, "turns", finite_integer)
            if facts.get("transcript_path")
            else None
        ),
        "lines_added": optional_number(money, "lines_added", finite_integer),
        "lines_removed": optional_number(money, "lines_removed", finite_integer),
        "session_title": identity.get("session_title"),
        "started_at": aggregate.get("started"),
        "updated_at": ledger.iso(now),
    }
    if "run_cost_usd" in money and aggregate.get("session_complete"):
        row["cost_usd"] = finite_number(aggregate.get("session"))
    return {key: value for key, value in row.items() if value is not None}


def _prune_marker():
    return state("session-metrics-prune.json")


def _prune(now, keep):
    root = os.path.dirname(os.fspath(_prune_marker()))
    rows = []
    for entry in os.scandir(root):
        if not entry.name.startswith(FILE_PREFIX) or not entry.name.endswith(FILE_SUFFIX):
            continue
        if not entry.is_file(follow_symlinks=False):
            continue
        snapshot = read_json(entry.path, {})
        updated = ledger.epoch(snapshot.get("updated_at")) if snapshot else 0.0
        expired = updated <= 0 or now - updated > RETENTION_SECONDS
        if expired:
            if entry.path != keep:
                expected = dict(snapshot)
                remove_json_if(
                    entry.path,
                    lambda current, prior=expected: current == prior
                    and (
                        ledger.epoch(current.get("updated_at")) <= 0
                        or now - ledger.epoch(current.get("updated_at")) > RETENTION_SECONDS
                    ),
                )
            continue
        rows.append((updated, entry.name, entry.path, dict(snapshot)))

    excess = max(0, len(rows) - MAX_SESSION_FILES)
    candidates = sorted(row for row in rows if row[2] != keep)
    for _updated, _name, path, snapshot in candidates[:excess]:
        remove_json_if(path, lambda current, prior=snapshot: current == prior)


def _maybe_prune(now, keep):
    def claim(marker):
        previous = ledger.epoch(marker.get("last_pruned_at"))
        if previous and 0 <= now - previous < PRUNE_INTERVAL_SECONDS:
            return False, False
        marker.clear()
        marker["last_pruned_at"] = ledger.iso(now)
        return True, True

    if update_json(_prune_marker(), {}, claim):
        _prune(now, keep)


def write_snapshot(facts, aggregate, now=None):
    """Atomically publish one normalized snapshot and maintain bounded retention."""
    if not enabled():
        return None
    observed = time.time() if now is None else now
    snapshot = _snapshot(facts, aggregate, observed)
    if snapshot is None:
        return None
    path = path_for(snapshot["session_id"])

    def replace(current):
        changed = current != snapshot
        current.clear()
        current.update(snapshot)
        return changed, dict(snapshot)

    result = update_json(path, {}, replace)
    _maybe_prune(observed, os.fspath(path))
    return result


def read_snapshot(session_id):
    """Read one current supported snapshot, or return None."""
    if not isinstance(session_id, str) or not session_id:
        return None
    snapshot = read_json(path_for(session_id), {})
    if (
        not isinstance(snapshot, Mapping)
        or snapshot.get("schema_version") != SCHEMA_VERSION
        or snapshot.get("session_id") != session_id
    ):
        return None
    return dict(snapshot)


def cli(argv):
    if len(argv) != 1:
        print("usage: agent-statusline metrics <session-id>", file=sys.stderr)
        return 2
    snapshot = read_snapshot(argv[0])
    if snapshot is None:
        print("no metrics for that session", file=sys.stderr)
        return 1
    print(json.dumps(snapshot, sort_keys=True))
    return 0
