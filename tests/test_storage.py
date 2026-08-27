"""Private atomic state and concurrent update behavior."""

import json
import os
import stat
import subprocess
import sys

from agent_statusline import storage


def test_private_text_publish_is_atomic_and_mode_600(tmp_path):
    path = tmp_path / "state.json"
    storage.write_text(str(path), '{"ok": true}\n')
    assert json.loads(path.read_text()) == {"ok": True}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".state.json.*"))


def test_jsonl_append_suppresses_only_unchanged_selected_facts(tmp_path):
    path = str(tmp_path / "history.jsonl")
    keys = ("five", "weekly")
    assert storage.append_json_if_changed(path, {"five": 10, "weekly": 20, "at": 1}, keys)
    assert not storage.append_json_if_changed(path, {"five": 10, "weekly": 20, "at": 2}, keys)
    assert storage.append_json_if_changed(path, {"five": 11, "weekly": 20, "at": 3}, keys)
    lines = (tmp_path / "history.jsonl").read_text().splitlines()
    assert [json.loads(line)["at"] for line in lines] == [1, 3]


def test_jsonl_history_is_bounded_and_malformed_rows_are_discarded(tmp_path):
    path = tmp_path / "history.jsonl"
    path.write_text('{"value": 0}\nnot-json\n')
    for value in range(1, 6):
        storage.append_json_if_changed(str(path), {"value": value}, ("value",), max_records=3)

    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert records == [{"value": 3}, {"value": 4}, {"value": 5}]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_jsonl_byte_bound_compacts_without_changing_the_latest_record(tmp_path):
    path = tmp_path / "history.jsonl"
    for value in range(20):
        storage.append_json_if_changed(
            str(path), {"value": value, "padding": "x" * 30}, ("value",), max_bytes=180
        )

    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert path.stat().st_size <= 180
    assert records[-1]["value"] == 19


def test_bounded_jsonl_hot_path_reads_only_the_tail(tmp_path, monkeypatch):
    path = tmp_path / "history.jsonl"
    path.write_text('{"value": 1}\n')
    monkeypatch.setattr(
        storage,
        "_jsonl_records",
        lambda _path: (_ for _ in ()).throw(AssertionError("full scan")),
    )

    assert not storage.append_json_if_changed(str(path), {"value": 1}, ("value",), max_bytes=1024)


def test_concurrent_json_transactions_lose_no_updates(tmp_path):
    path = tmp_path / "counter.json"
    code = r"""
import sys
from agent_statusline.storage import update_json

path = sys.argv[1]
for _ in range(20):
    def increment(data):
        data["count"] = data.get("count", 0) + 1
        return True, None
    update_json(path, {"count": 0}, increment)
"""
    env = dict(os.environ)
    source = os.path.abspath("src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    processes = [
        subprocess.Popen([sys.executable, "-c", code, str(path)], env=env) for _ in range(6)
    ]
    assert [process.wait(timeout=20) for process in processes] == [0] * 6
    assert json.loads(path.read_text()) == {"count": 120}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_wrong_json_shape_is_replaced_by_the_declared_default(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("[]")

    def add(data):
        data["ok"] = True
        return True, None

    storage.update_json(str(path), {}, add)
    assert json.loads(path.read_text()) == {"ok": True}
