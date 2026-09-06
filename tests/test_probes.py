"""Probe-cache transactions and malformed-state behavior."""

import json
import os
import subprocess
import sys

from agent_statusline import probes


def test_fresh_cached_value_avoids_probe(tmp_path, monkeypatch):
    state = tmp_path / "probes.json"
    state.write_text('{"key":{"at":100,"val":"cached"}}')
    monkeypatch.setattr(probes, "STATE", str(state))
    monkeypatch.setattr(probes.time, "time", lambda: 101)
    called = []

    assert probes.probe("key", 10, lambda: called.append(True)) == "cached"
    assert called == []


def test_stale_value_is_replaced(tmp_path, monkeypatch):
    state = tmp_path / "probes.json"
    state.write_text('{"key":{"at":1,"val":"old"}}')
    monkeypatch.setattr(probes, "STATE", str(state))
    monkeypatch.setattr(probes.time, "time", lambda: 100)

    assert probes.probe("key", 10, lambda: "new") == "new"
    assert json.loads(state.read_text())["key"] == {"at": 100, "val": "new"}


def test_malformed_nested_rows_degrade_and_later_values_are_usable(tmp_path, monkeypatch):
    state = tmp_path / "probes.json"
    state.write_text(
        json.dumps(
            {
                "list": [],
                "scalar": "bad",
                "bad-at": {"at": [], "val": "bad"},
                "infinite": {"at": float("inf"), "val": "bad"},
                "valid": {"at": 99, "val": "keep"},
            }
        )
    )
    monkeypatch.setattr(probes, "STATE", str(state))
    monkeypatch.setattr(probes.time, "time", lambda: 100)

    assert probes.probe("list", 10, lambda: "list-ok") == "list-ok"
    assert probes.probe("scalar", 10, lambda: "scalar-ok") == "scalar-ok"
    assert probes.probe("bad-at", 10, lambda: "at-ok") == "at-ok"
    assert probes.probe("infinite", 10, lambda: "finite-ok") == "finite-ok"
    assert probes.probe("valid", 10, lambda: "changed") == "keep"

    cache = json.loads(state.read_text())
    assert cache["list"]["val"] == "list-ok"
    assert cache["scalar"]["val"] == "scalar-ok"
    assert cache["bad-at"]["val"] == "at-ok"
    assert cache["infinite"]["val"] == "finite-ok"
    assert cache["valid"]["val"] == "keep"


def test_probe_exception_is_cached_as_none(tmp_path, monkeypatch):
    state = tmp_path / "probes.json"
    monkeypatch.setattr(probes, "STATE", str(state))

    def fail():
        raise RuntimeError("probe failed")

    assert probes.probe("key", 10, fail) is None
    assert json.loads(state.read_text())["key"]["val"] is None


def test_concurrent_distinct_probe_keys_are_all_preserved(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    env = dict(os.environ)
    env["AGENT_STATUSLINE_STATE"] = str(state_dir)
    env["HOME"] = str(tmp_path / "home")
    source = os.path.abspath("src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    code = r"""
import sys
from agent_statusline.probes import probe
key = sys.argv[1]
assert probe(key, 60, lambda: key) == key
"""
    processes = [
        subprocess.Popen([sys.executable, "-c", code, f"key-{number}"], env=env)
        for number in range(10)
    ]

    assert [process.wait(timeout=20) for process in processes] == [0] * 10
    cache = json.loads((state_dir / "statusline-probe-cache.json").read_text())
    assert {key: row["val"] for key, row in cache.items()} == {
        f"key-{number}": f"key-{number}" for number in range(10)
    }


def test_concurrent_same_key_publication_keeps_one_complete_value(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    env = dict(os.environ)
    env["AGENT_STATUSLINE_STATE"] = str(state_dir)
    env["HOME"] = str(tmp_path / "home")
    source = os.path.abspath("src")
    env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
    code = r"""
import sys, time
from agent_statusline.probes import probe
value = sys.argv[1]
result = probe("shared", 60, lambda: (time.sleep(0.02), value)[1])
assert result in {"left", "right"}
"""
    processes = [
        subprocess.Popen([sys.executable, "-c", code, value], env=env)
        for value in ("left", "right")
    ]

    assert [process.wait(timeout=20) for process in processes] == [0, 0]
    cache = json.loads((state_dir / "statusline-probe-cache.json").read_text())
    assert cache["shared"]["val"] in {"left", "right"}
    assert set(cache) == {"shared"}
