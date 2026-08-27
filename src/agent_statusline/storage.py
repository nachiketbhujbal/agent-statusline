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


def write_text(path, text):
    """Atomically publish private UTF-8 text."""
    directory = os.path.dirname(path)
    with locked(path):
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


def append_json_if_changed(path, record, keys):
    """Append one private JSONL record unless the selected facts are unchanged."""
    with locked(path):
        previous = None
        try:
            with open(path, "rb") as fh:
                fh.seek(max(0, os.path.getsize(path) - 4096))
                lines = fh.read().decode("utf-8", "replace").strip().splitlines()
            if lines:
                previous = json.loads(lines[-1])
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            pass
        if previous and all(previous.get(key) == record.get(key) for key in keys):
            return False
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return True


def _sync_directory(directory):
    try:
        fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass
