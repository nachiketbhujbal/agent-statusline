"""Private atomic state, entry safety, and concurrent update behavior."""

import json
import os
import stat
import subprocess
import sys

import pytest

from agent_statusline import paths, storage


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def test_absent_state_root_is_created_private(tmp_path, monkeypatch):
    root = tmp_path / "new" / "state"
    monkeypatch.setattr(paths, "STATE_DIR", str(root))

    assert paths.state("value.json") == str(root / "value.json")
    assert mode(root) == 0o700


def test_existing_state_root_mode_is_not_changed(tmp_path, monkeypatch):
    root = tmp_path / "state"
    root.mkdir(mode=0o750)
    root.chmod(0o750)
    monkeypatch.setattr(paths, "STATE_DIR", str(root))

    assert paths.state("value.json") == str(root / "value.json")
    assert mode(root) == 0o750


def test_symlinked_state_root_resolves_once(tmp_path, monkeypatch):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "state"
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(paths, "STATE_DIR", str(link))

    assert paths.state("value.json") == str(target / "value.json")


@pytest.mark.parametrize("name", ["", ".", "..", "../value.json", "nested/value.json"])
def test_state_rejects_non_direct_entries(tmp_path, monkeypatch, name):
    monkeypatch.setattr(paths, "STATE_DIR", str(tmp_path))
    with pytest.raises(ValueError):
        paths.state(name)


def test_private_text_publish_is_atomic_and_modes_are_private(tmp_path):
    path = tmp_path / "state.json"
    storage.write_text(path, '{"ok": true}\n')

    assert json.loads(path.read_text()) == {"ok": True}
    assert mode(path) == 0o600
    assert mode(str(path) + ".lock") == 0o600
    assert not list(tmp_path.glob(".state.json.*"))


def test_existing_state_mode_is_narrowed_but_directory_is_unchanged(tmp_path):
    tmp_path.chmod(0o750)
    path = tmp_path / "state.json"
    path.write_text("{}")
    path.chmod(0o644)

    assert storage.read_json(path, {}) == {}
    assert mode(path) == 0o600
    assert mode(tmp_path) == 0o750


def test_jsonl_append_suppresses_only_unchanged_selected_facts(tmp_path):
    path = tmp_path / "history.jsonl"
    keys = ("five", "weekly")
    assert storage.append_json_if_changed(path, {"five": 10, "weekly": 20, "at": 1}, keys)
    assert not storage.append_json_if_changed(path, {"five": 10, "weekly": 20, "at": 2}, keys)
    assert storage.append_json_if_changed(path, {"five": 11, "weekly": 20, "at": 3}, keys)
    assert [json.loads(line)["at"] for line in path.read_text().splitlines()] == [1, 3]
    assert mode(path) == 0o600


def test_jsonl_append_separates_a_truncated_final_line(tmp_path):
    path = tmp_path / "history.jsonl"
    path.write_text('{"old":')

    storage.append_json_if_changed(path, {"old": 2}, ("old",))

    assert path.read_text().splitlines() == ['{"old":', '{"old": 2}']


def test_concurrent_json_transactions_lose_no_updates(tmp_path):
    path = tmp_path / "counter.json"
    code = r"""
import sys
from agent_statusline.storage import update_json

path = sys.argv[1]
for _ in range(30):
    def increment(data):
        data["count"] = data.get("count", 0) + 1
        return True, None
    update_json(path, {"count": 0}, increment)
"""
    env = dict(os.environ)
    source = os.path.abspath("src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    processes = [
        subprocess.Popen([sys.executable, "-c", code, str(path)], env=env) for _ in range(8)
    ]
    assert [process.wait(timeout=30) for process in processes] == [0] * 8
    assert json.loads(path.read_text()) == {"count": 240}
    assert mode(path) == 0o600


def test_concurrent_identical_jsonl_appends_are_deduplicated(tmp_path):
    path = tmp_path / "history.jsonl"
    code = r"""
import sys
from agent_statusline.storage import append_json_if_changed
append_json_if_changed(sys.argv[1], {"value": 7, "at": 1}, ("value",))
"""
    env = dict(os.environ)
    source = os.path.abspath("src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    processes = [
        subprocess.Popen([sys.executable, "-c", code, str(path)], env=env) for _ in range(8)
    ]
    assert [process.wait(timeout=20) for process in processes] == [0] * 8
    assert path.read_text().splitlines() == ['{"value": 7, "at": 1}']


@pytest.mark.parametrize("contents,default", [("not json", {}), ("[]", {}), ("{}", [])])
def test_malformed_or_wrong_json_shape_returns_a_fresh_default(tmp_path, contents, default):
    path = tmp_path / "state.json"
    path.write_text(contents)

    result = storage.read_json(path, default)

    assert result == default
    assert result is not default


def test_wrong_json_shape_is_replaced_by_the_declared_default(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("[]")

    def add(data):
        data["ok"] = True
        return True, None

    storage.update_json(path, {}, add)
    assert json.loads(path.read_text()) == {"ok": True}


@pytest.mark.parametrize("operation", ["read", "write"])
def test_state_file_symlink_is_refused_without_touching_outside_target(tmp_path, operation):
    outside = tmp_path / "outside.json"
    outside.write_text('{"sentinel": true}\n')
    outside.chmod(0o640)
    path = tmp_path / "state.json"
    path.symlink_to(outside)
    before = outside.read_bytes(), mode(outside)

    with pytest.raises(storage.UnsafeStateError):
        if operation == "read":
            storage.read_json(path, {})
        else:
            storage.write_text(path, "replacement")

    assert (outside.read_bytes(), mode(outside)) == before
    assert path.is_symlink()


def test_lock_file_symlink_is_refused_without_touching_outside_target(tmp_path):
    outside = tmp_path / "outside.lock"
    outside.write_text("sentinel")
    outside.chmod(0o640)
    path = tmp_path / "state.json"
    (tmp_path / "state.json.lock").symlink_to(outside)
    before = outside.read_bytes(), mode(outside)

    with pytest.raises(storage.UnsafeStateError):
        storage.read_json(path, {})

    assert (outside.read_bytes(), mode(outside)) == before


@pytest.mark.parametrize("entry", ["state", "lock"])
def test_non_regular_entry_is_refused(tmp_path, entry):
    path = tmp_path / "state.json"
    unsafe = path if entry == "state" else tmp_path / "state.json.lock"
    os.mkfifo(unsafe)

    with pytest.raises(storage.UnsafeStateError):
        storage.read_json(path, {})


@pytest.mark.parametrize("failure", ["serialize", "fsync", "replace"])
def test_publication_failure_preserves_old_bytes_cleans_temp_and_releases_lock(
    tmp_path, monkeypatch, failure
):
    path = tmp_path / "state.json"
    storage.write_text(path, "old\n")
    old = path.read_bytes()

    if failure == "serialize":
        original_dump = storage.json.dump

        def fail_dump(*args, **kwargs):
            raise OSError("injected serialize failure")

        monkeypatch.setattr(storage.json, "dump", fail_dump)
    elif failure == "fsync":
        original_fsync = storage.os.fsync

        def fail_fsync(_fd):
            raise OSError("injected fsync failure")

        monkeypatch.setattr(storage.os, "fsync", fail_fsync)
    else:
        original_replace = storage.os.replace

        def fail_replace(_source, _target):
            raise OSError("injected replace failure")

        monkeypatch.setattr(storage.os, "replace", fail_replace)

    with pytest.raises(OSError, match="injected"):
        storage._publish_json_unlocked(path, {"new": True})

    assert path.read_bytes() == old
    assert not list(tmp_path.glob(".state.json.*"))

    if failure == "serialize":
        monkeypatch.setattr(storage.json, "dump", original_dump)
    elif failure == "fsync":
        monkeypatch.setattr(storage.os, "fsync", original_fsync)
    else:
        monkeypatch.setattr(storage.os, "replace", original_replace)
    storage.write_text(path, "retry\n")
    assert path.read_text() == "retry\n"


def test_directory_sync_failure_does_not_undo_successful_publication(tmp_path, monkeypatch):
    path = tmp_path / "state.json"

    def fail_sync(_directory):
        raise OSError("directory sync unavailable")

    monkeypatch.setattr(storage, "_sync_directory", fail_sync)
    storage.write_text(path, "published\n")
    assert path.read_text() == "published\n"


def test_updater_failure_releases_lock_and_does_not_publish(tmp_path):
    path = tmp_path / "state.json"
    storage.write_text(path, '{"value": 1}\n')

    def fail(_data):
        raise RuntimeError("updater failed")

    with pytest.raises(RuntimeError, match="updater failed"):
        storage.update_json(path, {}, fail)

    assert json.loads(path.read_text()) == {"value": 1}
    storage.write_text(path, '{"value": 2}\n')
    assert json.loads(path.read_text()) == {"value": 2}
