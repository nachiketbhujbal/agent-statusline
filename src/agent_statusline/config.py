"""Read-only user configuration, separate from host settings and runtime state."""

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path

ROW_IDS = (
    "PROJECT",
    "MODEL",
    "CONTEXT",
    "USAGE",
    "COST",
    "SYSTEM",
    "TOOLS",
    "CACHE",
    "TOKENS",
    "TIMING",
)
FIELD_CATALOG = {
    "PROJECT": {
        "directory": "Project directory and current subdirectory",
        "added_dirs": "Additional workspace directories",
        "branch": "Git branch and working tree status",
        "session_name": "Session title",
    },
    "MODEL": {
        "model": "Model name and reasoning effort",
        "thinking": "Extended thinking status",
        "fast_mode": "Fast mode status",
        "permission_mode": "Claude Code permission mode",
        "output_style": "Custom output style",
        "service_tier": "Nonstandard service tier",
        "version": "Claude Code version",
    },
    "CONTEXT": {
        "window": "Context use, token count and visual warning",
        "session_throughput": "Session tokens and turn statistics",
    },
    "USAGE": {
        "five_hour": "Five-hour rate-limit window",
        "seven_day": "Seven-day rate-limit window",
    },
    "COST": {
        "session": "Lifetime session cost and resume details",
        "rolling": "Cost over 24 hours, 7 days and 30 days",
        "history": "Recent and all-time cost with session counts",
        "lines": "Lines added and removed",
        "credits": "Usage credit status",
    },
    "SYSTEM": {
        "session_processes": "Current session process memory and count",
        "all_claude": "Machine-wide Claude process memory and count",
        "memory": "System memory pressure",
        "disk": "Workspace filesystem usage and free space",
    },
    "TOOLS": {
        "calls": "Total tool calls",
        "top_tools": "Most-used tools",
        "tool_errors": "Tool error count",
        "api_errors": "API error count",
        "files": "Distinct files edited and read",
        "subagents": "Subagent messages",
        "compactions": "Context compaction count",
        "commands": "Most-used slash commands",
    },
    "CACHE": {
        "hit_rate": "Cache read share of served input tokens",
        "ttl": "Cache lifetime and expiry",
        "relative_cost": "Relative cost compared with uncached input",
        "writes": "Cache writes by lifetime bucket",
    },
    "TOKENS": {
        "total": "Cumulative reused, written and uncached tokens",
        "turn": "Most recent turn's reused, written and uncached tokens",
    },
    "TIMING": {
        "turn_duration": "Turn duration statistics",
        "wall_api": "Wall time and API time",
        "hooks": "Hook timing and errors",
    },
}
MAX_BYTES = 64 * 1024
DEFAULT_WARN = 80.0
VALID_EVENTS = frozenset({"stop", "submit", "both"})


@dataclass(frozen=True)
class Config:
    warn_pct: float = DEFAULT_WARN
    warn_event: str = "stop"
    warn_message: str | None = None
    metrics_enabled: bool = True
    color: str = "default"
    hidden_rows: frozenset[str] = frozenset()
    fields: tuple[tuple[str, frozenset[str]], ...] = ()


DEFAULTS = Config()


class InvalidConfig(ValueError):
    """A diagnostic assembled from known keys, never file values."""


def config_path(environ=None):
    source = os.environ if environ is None else environ
    base = Path(source.get("XDG_CONFIG_HOME") or "")
    if not base.is_absolute():
        base = Path.home() / ".config"
    return base / "agent-statusline" / "config.toml"


def _table(value, name, keys):
    if not isinstance(value, dict):
        raise InvalidConfig(f"{name}: expected a table")
    if value.keys() - keys:
        raise InvalidConfig(f"{name}: unknown key")
    return value


def _validate(doc) -> Config:
    _table(
        doc,
        "configuration",
        {"schema_version", "context_guard", "session_metrics", "display"},
    )
    version = doc.get("schema_version")
    if type(version) is not int or version != 1:
        raise InvalidConfig("schema_version: expected integer 1")

    guard = _table(
        doc.get("context_guard", {}),
        "context_guard",
        {"warn_pct", "warn_event", "warn_message"},
    )
    pct = guard.get("warn_pct", DEFAULTS.warn_pct)
    if type(pct) not in (int, float) or not 1 <= pct <= 100:
        raise InvalidConfig("context_guard.warn_pct: expected a finite number from 1 through 100")
    event = guard.get("warn_event", DEFAULTS.warn_event)
    if not isinstance(event, str) or event not in VALID_EVENTS:
        raise InvalidConfig("context_guard.warn_event: expected stop, submit or both")
    message = guard.get("warn_message")
    if message is not None and (not isinstance(message, str) or "{pct}" not in message):
        raise InvalidConfig("context_guard.warn_message: expected a message containing {pct}")

    metrics = _table(doc.get("session_metrics", {}), "session_metrics", {"enabled"})
    enabled = metrics.get("enabled", DEFAULTS.metrics_enabled)
    if not isinstance(enabled, bool):
        raise InvalidConfig("session_metrics.enabled: expected a boolean")

    display = _table(doc.get("display", {}), "display", {"color", "rows", "fields"})
    color = display.get("color", DEFAULTS.color)
    if color not in ("default", "plain"):
        raise InvalidConfig("display.color: expected default or plain")
    rows = _table(display.get("rows", {}), "display.rows", set(ROW_IDS))
    for row_id, visibility in rows.items():
        if visibility not in ("show", "hide"):
            raise InvalidConfig(f"display.rows.{row_id}: expected show or hide")

    fields = _table(display.get("fields", {}), "display.fields", set(FIELD_CATALOG))
    selections = []
    for row_id, ids in fields.items():
        key = f"display.fields.{row_id}"
        if not isinstance(ids, list) or not ids:
            raise InvalidConfig(f"{key}: expected a nonempty array of field IDs")
        if any(not isinstance(field, str) or field not in FIELD_CATALOG[row_id] for field in ids):
            raise InvalidConfig(f"{key}: unknown field ID")
        if len(set(ids)) != len(ids):
            raise InvalidConfig(f"{key}: duplicate field ID")
        selections.append((row_id, frozenset(ids)))

    return Config(
        float(pct),
        event,
        message,
        enabled,
        color,
        frozenset(key for key, visibility in rows.items() if visibility == "hide"),
        tuple(selections),
    )


def _read_document(path: Path) -> dict | None:
    """Read a bounded, regular TOML file, or return None when absent."""
    try:
        # Refuse non-regular files without waiting on a FIFO.
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise InvalidConfig("expected a regular configuration file")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                data = stream.read(MAX_BYTES + 1)
        finally:
            os.close(fd)
    except FileNotFoundError:
        return None
    except OSError:
        raise InvalidConfig("cannot read configuration file") from None
    if len(data) > MAX_BYTES:
        raise InvalidConfig("configuration file exceeds 64 KiB")

    # Avoid loading the parser on the default no-file path.
    import tomllib

    try:
        return tomllib.loads(data.decode("utf-8"))
    except (ValueError, RecursionError):
        raise InvalidConfig("invalid UTF-8 or TOML syntax") from None


def read_config(path: Path) -> Config | None:
    """Return validated settings, or None when the file is absent."""
    doc = _read_document(path)
    return None if doc is None else _validate(doc)


def load_config(environ=None) -> Config:
    """A bad optional file must not interrupt rendering or hooks."""
    try:
        return read_config(config_path(environ)) or DEFAULTS
    except (InvalidConfig, RuntimeError):
        return DEFAULTS


def _list_fields(row_ids):
    if len(row_ids) > 1:
        print("usage: agent-statusline config fields [ROW]", file=sys.stderr)
        return 2
    if row_ids and row_ids[0] not in FIELD_CATALOG:
        print("config fields: unknown row ID", file=sys.stderr)
        return 2
    for row in row_ids or ROW_IDS:
        print(row)
        for field, description in FIELD_CATALOG[row].items():
            print(f"  {field}  {description}")
    return 0


def _show_config():
    from agent_statusline import session_metrics
    from agent_statusline.hooks import context_guard

    try:
        doc = _read_document(config_path())
        settings = DEFAULTS if doc is None else _validate(doc)
    except (InvalidConfig, RuntimeError):
        print("configuration: invalid or unreadable file. Using defaults and environment")
        doc = None
        settings = DEFAULTS
    else:
        print("configuration: no file" if doc is None else "configuration: TOML loaded")
    doc = doc or {}

    def show(section, key, value, table, env=None):
        if env is not None and env in os.environ:
            source = env
        else:
            source = "TOML" if key in table else "default"
        print(f"{section}.{key} = {value} [{source}]")

    guard, error = context_guard.configuration(os.environ, file_config=settings)
    if error:
        print(f"context_guard: disabled ({error})")
    else:
        guard_table = doc.get("context_guard", {})
        show(
            "context_guard",
            "warn_pct",
            guard["threshold"],
            guard_table,
            context_guard.THRESHOLD_ENV,
        )
        show(
            "context_guard",
            "warn_event",
            guard["event"],
            guard_table,
            context_guard.EVENT_ENV,
        )
        message = "custom (redacted)" if guard["message"] is not None else "built-in"
        show(
            "context_guard",
            "warn_message",
            message,
            guard_table,
            context_guard.MESSAGE_ENV,
        )

    enabled = session_metrics.enabled(os.environ, file_default=settings.metrics_enabled)
    show(
        "session_metrics",
        "enabled",
        str(enabled).lower(),
        doc.get("session_metrics", {}),
        session_metrics.OPT_OUT_ENV,
    )
    display = doc.get("display", {})
    show("display", "color", settings.color, display)
    rows = display.get("rows", {})
    fields = display.get("fields", {})
    selections = dict(settings.fields)
    for row in ROW_IDS:
        visibility = "hide" if row in settings.hidden_rows else "show"
        show("display.rows", row, visibility, rows)
        selected = selections.get(row)
        groups = (
            "all"
            if selected is None
            else ", ".join(field for field in FIELD_CATALOG[row] if field in selected)
        )
        show("display.fields", row, groups, fields)
    return 0


EXAMPLE = """# Optional agent-statusline settings. Uncomment entries to change the view.
schema_version = 1

[display]
# color = "plain"

[display.rows]
# CACHE = "hide"

[display.fields]
# PROJECT = ["directory", "branch", "session_name"]

[context_guard]
# warn_pct = 80
# warn_event = "stop"
# warn_message = "Context is at {pct}%."

[session_metrics]
# enabled = false
"""


def cli(argv):
    if argv == ["example"]:
        print(EXAMPLE, end="")
        return 0
    if argv == ["show"]:
        return _show_config()
    if argv[:1] == ["fields"]:
        return _list_fields(argv[1:])
    if argv != ["check"]:
        print("usage: agent-statusline config {check,fields [ROW],show,example}", file=sys.stderr)
        return 2
    try:
        config = read_config(config_path())
    except InvalidConfig as error:
        print(f"config check: {error}", file=sys.stderr)
        return 1
    except RuntimeError:
        print("config check: cannot resolve configuration directory", file=sys.stderr)
        return 1
    print("config check: valid" if config is not None else "config check: no file; defaults apply")
    return 0
