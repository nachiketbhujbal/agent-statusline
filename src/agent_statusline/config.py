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
    _table(doc, "configuration", {"schema_version", "context_guard", "session_metrics", "display"})
    version = doc.get("schema_version")
    if type(version) is not int or version != 1:
        raise InvalidConfig("schema_version: expected integer 1")

    guard = _table(
        doc.get("context_guard", {}), "context_guard", {"warn_pct", "warn_event", "warn_message"}
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

    display = _table(doc.get("display", {}), "display", {"color", "rows"})
    color = display.get("color", DEFAULTS.color)
    if color not in ("default", "plain"):
        raise InvalidConfig("display.color: expected default or plain")
    rows = _table(display.get("rows", {}), "display.rows", set(ROW_IDS))
    for row_id, visibility in rows.items():
        if visibility not in ("show", "hide"):
            raise InvalidConfig(f"display.rows.{row_id}: expected show or hide")

    return Config(
        float(pct),
        event,
        message,
        enabled,
        color,
        frozenset(key for key, visibility in rows.items() if visibility == "hide"),
    )


def read_config(path: Path) -> Config | None:
    """Return validated settings, or None when the file is absent."""
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
        doc = tomllib.loads(data.decode("utf-8"))
    except (ValueError, RecursionError):
        raise InvalidConfig("invalid UTF-8 or TOML syntax") from None
    return _validate(doc)


def load_config(environ=None) -> Config:
    """A bad optional file must not interrupt rendering or hooks."""
    try:
        return read_config(config_path(environ)) or DEFAULTS
    except (InvalidConfig, RuntimeError):
        return DEFAULTS


def cli(argv):
    if argv != ["check"]:
        print("usage: agent-statusline config check", file=sys.stderr)
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
