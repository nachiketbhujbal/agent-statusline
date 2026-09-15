"""Private, locked, atomic persistence for package-owned runtime state."""

import contextlib
import copy
import fcntl
import json
import os
import stat
from collections.abc import Mapping


class UnsafeStateError(OSError):
    """A state or lock entry is not a direct regular file."""


def _entry(path):
    """Resolve a parent once while leaving its final state filename unresolved."""
    raw = os.path.abspath(os.fspath(path))
    name = os.path.basename(raw)
    if not name or name in (".", ".."):
        raise UnsafeStateError(f"unsafe state entry: {raw}")
    directory = os.path.realpath(os.path.dirname(raw))
    info = os.stat(directory)
    if not stat.S_ISDIR(info.st_mode):
        raise UnsafeStateError(f"state parent is not a directory: {directory}")
    return os.path.join(directory, name)


def _validate_entry(path):
    """Return True for an existing regular file, False when it is absent."""
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode):
        raise UnsafeStateError(f"state entry is not a regular file: {path}")
    return True


def _close_after_error(fd):
    try:
        os.close(fd)
    except OSError:
        pass


def _open_regular(path, flags, mode=None):
    """Open a direct regular entry without following a final symlink."""
    _validate_entry(path)
    safe_flags = flags | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    # A nonblocking open prevents a swapped FIFO from hanging before fstat rejects it.
    safe_flags |= getattr(os, "O_NONBLOCK", 0)
    fd = None
    try:
        fd = os.open(path, safe_flags, mode) if mode is not None else os.open(path, safe_flags)
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise UnsafeStateError(f"state entry is not a regular file: {path}")
        return fd
    except BaseException:
        if fd is not None:
            _close_after_error(fd)
        raise


@contextlib.contextmanager
def locked(path, exclusive=True):
    """Hold a private sidecar lock for one state-file transaction."""
    target = _entry(path)
    lock_path = target + ".lock"
    fd = _open_regular(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        os.fchmod(fd, 0o600)
        operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
        fcntl.flock(fd, operation)
    except BaseException:
        _close_after_error(fd)
        raise

    try:
        yield target
    except BaseException:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        _close_after_error(fd)
        raise
    else:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _default(value):
    return value() if callable(value) else copy.deepcopy(value)


def _read_unlocked(path, default):
    fallback = _default(default)
    target = _entry(path)
    try:
        fd = _open_regular(target, os.O_RDONLY)
    except FileNotFoundError:
        return fallback

    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "r", encoding="utf-8") as fh:
            fd = None
            data = json.load(fh)
    except (UnicodeError, ValueError, RecursionError):
        return fallback
    finally:
        if fd is not None:
            _close_after_error(fd)
    return data if isinstance(data, type(fallback)) else fallback


def read_json(path, default):
    """Read JSON under a shared lock, returning a fresh default if malformed."""
    with locked(path, exclusive=False) as target:
        return _read_unlocked(target, default)


def _unlink_temporary(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
    except OSError:
        # Cleanup must not replace the primary publication failure.
        pass


def _open_temporary(target):
    """Create one private same-directory temporary without importing tempfile."""
    directory = os.path.dirname(target)
    prefix = f".{os.path.basename(target)}.{os.getpid()}.{os.urandom(12).hex()}"
    for attempt in range(128):
        temporary = os.path.join(directory, f"{prefix}.{attempt}")
        try:
            fd = _open_regular(temporary, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
        except FileExistsError:
            continue
        return fd, temporary
    raise FileExistsError(f"cannot create unique temporary for {target}")


def _atomic_publish_unlocked(path, writer):
    target = _entry(path)
    _validate_entry(target)
    directory = os.path.dirname(target)
    fd, temporary = _open_temporary(target)
    descriptor_owned = True
    published = False
    try:
        os.fchmod(fd, 0o600)
        handle = os.fdopen(fd, "w", encoding="utf-8")
        descriptor_owned = False
        with handle:
            writer(handle)
            handle.flush()
            os.fsync(handle.fileno())
        # Reject a destination changed into an unsupported entry before replace.
        _validate_entry(target)
        os.replace(temporary, target)
        published = True
        try:
            _sync_directory(directory)
        except OSError:
            pass
    except BaseException:
        if descriptor_owned:
            _close_after_error(fd)
        if not published:
            _unlink_temporary(temporary)
        raise


def _publish_json_unlocked(path, data):
    def serialize(handle):
        json.dump(data, handle, indent=2)
        handle.write("\n")

    _atomic_publish_unlocked(path, serialize)


def update_json(path, default, updater):
    """Hold one exclusive lock across a JSON read-modify-write transaction."""
    with locked(path) as target:
        data = _read_unlocked(target, default)
        changed, result = updater(data)
        if changed:
            _publish_json_unlocked(target, data)
        return result


def write_text(path, text):
    """Atomically publish private UTF-8 text."""
    with locked(path) as target:
        _atomic_publish_unlocked(target, lambda handle: handle.write(text))


def remove(path):
    """Remove one regular state entry while holding its package lock."""
    with locked(path) as target:
        if not _validate_entry(target):
            return False
        os.unlink(target)
        _sync_directory(os.path.dirname(target))
        return True


def _tail_record(path):
    """Return the last valid object and whether the existing file ends in newline."""
    try:
        fd = _open_regular(path, os.O_RDONLY)
    except FileNotFoundError:
        return None, True
    try:
        os.fchmod(fd, 0o600)
        size = os.fstat(fd).st_size
        os.lseek(fd, max(0, size - 4096), os.SEEK_SET)
        chunk = os.read(fd, 4096)
    finally:
        os.close(fd)

    previous = None
    for line in reversed(chunk.decode("utf-8", "replace").splitlines()):
        try:
            candidate = json.loads(line)
        except (ValueError, RecursionError):
            continue
        if isinstance(candidate, Mapping):
            previous = candidate
            break
    return previous, not chunk or chunk.endswith(b"\n")


def _jsonl_records(path):
    """Read valid JSON-object rows through a validated descriptor."""
    records: list[Mapping] = []
    try:
        fd = _open_regular(path, os.O_RDONLY)
    except FileNotFoundError:
        return records
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "rb") as fh:
            fd = None
            for raw_line in fh:
                try:
                    candidate = json.loads(raw_line.decode("utf-8"))
                except (UnicodeError, ValueError, RecursionError):
                    continue
                if isinstance(candidate, Mapping):
                    records.append(candidate)
    finally:
        if fd is not None:
            _close_after_error(fd)
    return records


def _bounded_jsonl_text(records, max_bytes):
    """Serialize the newest contiguous records that fit, always keeping newest."""
    retained: list[str] = []
    retained_bytes = 0
    for record in reversed(records):
        line = json.dumps(record) + "\n"
        line_bytes = len(line.encode("utf-8"))
        if retained and retained_bytes + line_bytes > max_bytes:
            break
        retained.append(line)
        retained_bytes += line_bytes
    retained.reverse()
    return "".join(retained)


def append_json_if_changed(path, record, keys, max_bytes=None):
    """Append one serialized JSONL record unless selected facts are unchanged."""
    if max_bytes is not None and (
        isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1
    ):
        raise ValueError("max_bytes must be a positive integer")

    with locked(path) as target:
        previous, ends_with_newline = _tail_record(target)
        unchanged = previous is not None and all(
            previous.get(key) == record.get(key) for key in keys
        )
        encoded = json.dumps(record) + "\n"

        size = 0
        if max_bytes is not None:
            try:
                fd = _open_regular(target, os.O_RDONLY)
            except FileNotFoundError:
                pass
            else:
                try:
                    size = os.fstat(fd).st_size
                finally:
                    os.close(fd)
            growth = 0 if unchanged else len(encoded.encode("utf-8")) + (not ends_with_newline)
            if size + growth > max_bytes:
                records = _jsonl_records(target)
                previous = records[-1] if records else None
                unchanged = previous is not None and all(
                    previous.get(key) == record.get(key) for key in keys
                )
                if not unchanged:
                    records.append(record)
                text = _bounded_jsonl_text(records, max_bytes)
                _atomic_publish_unlocked(target, lambda handle: handle.write(text))
                return not unchanged

        if unchanged:
            return False

        existed = _validate_entry(target)
        fd = _open_regular(target, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as fh:
                fd = None
                if not ends_with_newline:
                    fh.write("\n")
                fh.write(encoded)
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            if fd is not None:
                _close_after_error(fd)
        if not existed:
            _sync_directory(os.path.dirname(target))
        return True


def _sync_directory(directory):
    """Best-effort directory durability without leaking its descriptor."""
    fd = None
    try:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_DIRECTORY", 0)
        fd = os.open(directory, flags)
        os.fsync(fd)
    except OSError:
        pass
    finally:
        if fd is not None:
            _close_after_error(fd)
