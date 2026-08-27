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
    assert not storage.append_json_if_changed(
        path, {"five": 10, "weekly": 20, "at": 2}, keys
    )
    assert storage.append_json_if_changed(path, {"five": 11, "weekly": 20, "at": 3}, keys)
    lines = (tmp_path / "history.jsonl").read_text().splitlines()
    assert [json.loads(line)["at"] for line in lines] == [1, 3]


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
        subprocess.Popen([sys.executable, "-c", code, str(path)], env=env)
        for _ in range(6)
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
