"""Host acquisition adapters that emit one normalized fact shape.

The renderer consumes these groups instead of reaching into a host payload
directly.  A host omits facts it cannot supply; in particular, exact money is
never inferred from token counts.
"""

import os
from collections.abc import Mapping

from agent_statusline.coerce import finite_integer, finite_number
from agent_statusline.transcript import dig, transcript_totals

GROUPS = ("identity", "workspace", "model", "context", "tokens", "limits", "activity", "money")


def _text(value):
    return value if isinstance(value, str) else None


def _group(**values):
    return {key: value for key, value in values.items() if value is not None}


def claude_facts(payload, transcript_reader=transcript_totals, default_cwd=None):
    """Normalize one Claude Code status-line payload and its transcript facts."""
    if not isinstance(payload, Mapping):
        return None

    transcript_path = _text(payload.get("transcript_path"))
    activity = transcript_reader(transcript_path)
    if not isinstance(activity, Mapping):
        activity = {}

    cwd = _text(dig(payload, "workspace", "current_dir")) or _text(payload.get("cwd"))
    if cwd is None:
        cwd = default_cwd if isinstance(default_cwd, str) else os.getcwd()
    project_dir = _text(dig(payload, "workspace", "project_dir")) or cwd
    added_dirs = dig(payload, "workspace", "added_dirs", default=[])
    if not isinstance(added_dirs, list):
        added_dirs = []

    permission = activity.get("perm")
    if not isinstance(permission, str):
        permission = _text(payload.get("permission_mode"))

    current = dig(payload, "context_window", "current_usage", default={})
    if not isinstance(current, Mapping):
        current = {}
    current_tokens = {
        key: finite_integer(current.get(key))
        for key in (
            "input_tokens",
            "output_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        )
    }

    cost = dig(payload, "cost", default={})
    if not isinstance(cost, Mapping):
        cost = {}
    exact_cost = cost.get("total_cost_usd")
    run_cost = None if exact_cost is None else finite_number(exact_cost)

    limits = dig(payload, "rate_limits", default={})
    if not isinstance(limits, Mapping):
        limits = {}

    return {
        "host": "claude",
        "transcript_path": transcript_path,
        "identity": _group(
            session_id=_text(payload.get("session_id")),
            session_title=_text(payload.get("session_name")),
            client_version=_text(payload.get("version")),
        ),
        "workspace": {
            "cwd": cwd,
            "project_dir": project_dir,
            "added_dirs": added_dirs,
        },
        "model": _group(
            id=_text(dig(payload, "model", "id")),
            display_name=_text(dig(payload, "model", "display_name")),
            effort=_text(dig(payload, "effort", "level")),
            thinking=bool(dig(payload, "thinking", "enabled", default=False)),
            fast_mode=bool(payload.get("fast_mode")),
            permission_mode=permission,
            output_style=_text(dig(payload, "output_style", "name")),
            service_tier=_text(activity.get("tier")),
        ),
        "context": {
            "window_size": finite_integer(
                dig(payload, "context_window", "context_window_size", default=0)
            ),
            "used_percentage": finite_number(
                dig(payload, "context_window", "used_percentage", default=0)
            ),
            "current_tokens": current_tokens,
        },
        "tokens": {
            key: activity.get(key)
            for key in ("in", "cw", "cr", "out", "think", "turns", "b1h", "b5m")
        },
        "limits": {
            key: value
            for key, value in (
                ("five_hour", limits.get("five_hour")),
                ("seven_day", limits.get("seven_day")),
            )
            if isinstance(value, Mapping)
        },
        "activity": dict(activity),
        "money": _group(
            run_cost_usd=run_cost,
            wall_seconds=max(0.0, finite_number(cost.get("total_duration_ms")) / 1000),
            api_seconds=max(0.0, finite_number(cost.get("total_api_duration_ms")) / 1000),
            lines_added=finite_integer(cost.get("total_lines_added")),
            lines_removed=finite_integer(cost.get("total_lines_removed")),
        ),
    }
