"""Private, locked, atomic persistence for runtime state."""

import contextlib
import copy
import fcntl
import json
import os
import tempfile


@contextlib.contextmanager
def locked(path, exclusive=True):
    """Hold the sidecar lock for one state-file transaction."""
    lock_path = path + ".lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        os.fchmod(fd, 0o600)
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(fd, operation)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _default(value):
    return value() if callable(value) else copy.deepcopy(value)


def _read_unlocked(path, default):
    fallback = _default(default)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        os.chmod(path, 0o600)
        return data if isinstance(data, type(fallback)) else fallback
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return fallback


def read_json(path, default):
    """Read JSON under a shared lock, returning a fresh default on failure."""
    with locked(path, exclusive=False):
        return _read_unlocked(path, default)


def _publish_json_unlocked(path, data):
    directory = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.", dir=directory, text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _sync_directory(directory)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def update_json(path, default, updater):
    """Run an atomic JSON read-modify-write transaction.

    ``updater`` receives the decoded value and returns ``(changed, result)``.
    The file is published only when ``changed`` is true.
    """
    with locked(path):
        data = _read_unlocked(path, default)
        changed, result = updater(data)
        if changed:
            _publish_json_unlocked(path, data)
        return result


def _publish_text_unlocked(path, text):
    directory = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _sync_directory(directory)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def write_text(path, text):
    """Atomically publish private UTF-8 text."""
    with locked(path):
        _publish_text_unlocked(path, text)


def _jsonl_records(path):
    lines = []
    records = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for line in lines:
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                records.append(parsed)
    except (FileNotFoundError, OSError, UnicodeError):
        pass
    return lines, records


def append_json_if_changed(path, record, keys, max_records=None, max_bytes=None):
    """Append one private JSONL record unless the selected facts are unchanged."""
    with locked(path):
        size = 0
        try:
            size = os.path.getsize(path)
            with open(path, "rb") as fh:
                fh.seek(max(0, size - 4096))
                tail = fh.read().decode("utf-8", "replace").strip().splitlines()
            previous = json.loads(tail[-1]) if tail else None
            if not isinstance(previous, dict):
                previous = None
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            previous = None
        encoded = json.dumps(record) + "\n"
        appended = not previous or not all(previous.get(key) == record.get(key) for key in keys)
        compact_for_size = (
            max_bytes is not None and size + (len(encoded) if appended else 0) > max_bytes
        )
        if max_records is not None or compact_for_size:
            lines, records = _jsonl_records(path)
            previous = records[-1] if records else None
            appended = not previous or not all(previous.get(key) == record.get(key) for key in keys)
            if appended:
                records.append(record)
            compact = compact_for_size or len(records) != len(lines)
            if max_records is not None and len(records) > max_records:
                records = records[-max_records:]
                compact = True
            if max_bytes is not None:
                retained: list[dict] = []
                retained_bytes = 0
                for item in reversed(records):
                    item_bytes = len(json.dumps(item).encode("utf-8")) + 1
                    if retained and retained_bytes + item_bytes > max_bytes:
                        break
                    retained.append(item)
                    retained_bytes += item_bytes
                retained.reverse()
                if retained != records:
                    records = retained
                    compact = True
            if compact:
                text = "".join(json.dumps(item) + "\n" for item in records)
                _publish_text_unlocked(path, text)
                return appended
        if not appended:
            return False
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(encoded)
            fh.flush()
            os.fsync(fh.fileno())
        return appended


def _sync_directory(directory):
    try:
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass
