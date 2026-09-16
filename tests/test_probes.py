"""Probe-cache transactions and malformed-state behavior."""

import json
import os
import subprocess
import sys

import pytest

from agent_statusline import probes


def test_process_values_come_from_one_snapshot(monkeypatch):
    calls = []
    snapshot = """\
20 1 100 claude
99 20 10 python-statusline
30 20 50 child-tool
40 1 200 /opt/ClaudeCode.app/claude
"""

    def fake_run(*args, **_kwargs):
        calls.append(args)
        return snapshot

    monkeypatch.setattr(probes, "_run", fake_run)
    monkeypatch.setattr(probes.os, "getpid", lambda: 99)

    assert probes.processes() == {
        "mine_rss": 160 * 1024,
        "mine_pid": 20,
        "mine_procs": 3,
        "all_rss": 300 * 1024,
        "all_n": 2,
    }
    assert calls == [("ps", "-eo", "pid=,ppid=,rss=,command=")]


def test_linux_memory_uses_total_and_available(tmp_path, monkeypatch):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(
        "MemTotal:        8388608 kB\n"
        "MemFree:          262144 kB\n"
        "MemAvailable:    2097152 kB\n"
        "Cached:          1048576 kB\n"
    )
    monkeypatch.setattr(probes.sys, "platform", "linux")
    monkeypatch.setattr(probes, "PROC_MEMINFO", str(meminfo))

    assert probes.memory() == {
        "total": 8 * 1024**3,
        "used": 6 * 1024**3,
        "pct": 75.0,
    }


@pytest.mark.parametrize(
    "contents, expected",
    [
        ("MemAvailable: 1024 kB\n", {"total": 0}),
        ("MemTotal: 2048 kB\n", {"total": 2048 * 1024}),
        ("MemTotal: invalid kB\nMemAvailable: 1024 kB\n", {"total": 0}),
        ("MemTotal: 2048 MB\nMemAvailable: 1024 kB\n", {"total": 0}),
    ],
)
def test_linux_memory_degrades_when_required_values_are_unusable(
    tmp_path, monkeypatch, contents, expected
):
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(contents)
    monkeypatch.setattr(probes.sys, "platform", "linux")
    monkeypatch.setattr(probes, "PROC_MEMINFO", str(meminfo))

    assert probes.memory() == expected


def test_linux_memory_degrades_when_proc_meminfo_is_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(probes.sys, "platform", "linux")
    monkeypatch.setattr(probes, "PROC_MEMINFO", str(tmp_path / "missing"))

    assert probes.memory() == {"total": 0}


def test_macos_memory_retains_native_vm_stat_probe(monkeypatch):
    calls = []
    vm_stat = (
        "Mach Virtual Memory Statistics: (page size of 4096 bytes)\n"
        "Pages active: 100.\n"
        "Pages wired down: 50.\n"
        "Pages occupied by compressor: 25.\n"
    )

    def fake_run(*args, **_kwargs):
        calls.append(args)
        if args == ("sysctl", "-n", "hw.memsize"):
            return str(1000 * 4096)
        if args == ("vm_stat",):
            return vm_stat
        raise AssertionError(args)

    monkeypatch.setattr(probes.sys, "platform", "darwin")
    monkeypatch.setattr(probes, "_run", fake_run)

    assert probes.memory() == {
        "total": 1000 * 4096,
        "used": 175 * 4096,
        "pct": 17.5,
        "compressed": 25 * 4096,
    }
    assert calls == [("sysctl", "-n", "hw.memsize"), ("vm_stat",)]


def test_memory_degrades_on_an_unknown_platform(monkeypatch):
    monkeypatch.setattr(probes.sys, "platform", "plan9")

    assert probes.memory() == {"total": 0}


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


@pytest.mark.parametrize("observed", [10**1000, -(10**1000)])
def test_oversized_cache_timestamp_is_stale(tmp_path, monkeypatch, observed):
    state = tmp_path / "probes.json"
    state.write_text(json.dumps({"key": {"at": observed, "val": "bad"}}))
    monkeypatch.setattr(probes, "STATE", str(state))

    assert probes.probe("key", 10, lambda: "computed") == "computed"


def test_fresh_probe_prunes_invalid_future_and_expired_rows_without_recomputing(
    tmp_path, monkeypatch
):
    now = 2_000_000_000.0
    state = tmp_path / "probes.json"
    state.write_text(
        json.dumps(
            {
                "active": {"at": now - 1, "val": "cached"},
                "boundary": {"at": now - probes.MAX_CACHE_AGE_S, "val": "keep"},
                "expired": {"at": now - probes.MAX_CACHE_AGE_S - 1, "val": "drop"},
                "future": {"at": now + 1, "val": "drop"},
                "malformed": [],
            }
        )
    )
    monkeypatch.setattr(probes, "STATE", str(state))
    monkeypatch.setattr(probes.time, "time", lambda: now)
    called = []

    assert probes.probe("active", 10, lambda: called.append(True)) == "cached"

    assert called == []
    cache = json.loads(state.read_text())
    assert set(cache) == {"active", "boundary"}


def test_probe_cap_preserves_active_row_even_when_it_is_oldest(tmp_path, monkeypatch):
    now = 2_000_000_000.0
    state = tmp_path / "probes.json"
    rows = {
        "active": {"at": now - 100, "val": "cached"},
        **{
            f"recent:{index:03d}": {"at": now - index, "val": index}
            for index in range(probes.MAX_CACHE_ENTRIES)
        },
    }
    state.write_text(json.dumps(rows))
    monkeypatch.setattr(probes, "STATE", str(state))
    monkeypatch.setattr(probes.time, "time", lambda: now)

    assert probes.probe("active", 200, lambda: "replacement") == "cached"

    cache = json.loads(state.read_text())
    assert len(cache) == probes.MAX_CACHE_ENTRIES
    assert cache["active"]["val"] == "cached"
    assert "recent:255" not in cache


def test_probe_maintenance_failure_still_returns_fresh_cached_value(tmp_path, monkeypatch):
    now = 2_000_000_000.0
    state = tmp_path / "probes.json"
    state.write_text(
        json.dumps(
            {
                "active": {"at": now - 1, "val": "cached"},
                "expired": {"at": 0, "val": "drop"},
            }
        )
    )
    monkeypatch.setattr(probes, "STATE", str(state))
    monkeypatch.setattr(probes.time, "time", lambda: now)
    monkeypatch.setattr(
        probes,
        "update_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("publish failed")),
    )

    assert probes.probe("active", 10, lambda: "replacement") == "cached"


def test_probe_exception_is_cached_as_none(tmp_path, monkeypatch):
    state = tmp_path / "probes.json"
    monkeypatch.setattr(probes, "STATE", str(state))

    def fail():
        raise RuntimeError("probe failed")

    assert probes.probe("key", 10, fail) is None
    assert json.loads(state.read_text())["key"]["val"] is None


def test_storage_read_failure_degrades_to_computed_value(monkeypatch):
    def fail_read(_path, _default):
        raise OSError("read failed")

    monkeypatch.setattr(probes, "read_json", fail_read)
    monkeypatch.setattr(probes, "update_json", lambda _path, _default, update: update({})[1])

    assert probes.probe("key", 10, lambda: "computed") == "computed"


def test_storage_publication_failure_degrades_to_computed_value(tmp_path, monkeypatch):
    state = tmp_path / "probes.json"
    monkeypatch.setattr(probes, "STATE", str(state))

    def fail_update(_path, _default, _update):
        raise OSError("publish failed")

    monkeypatch.setattr(probes, "update_json", fail_update)

    assert probes.probe("key", 10, lambda: "computed") == "computed"


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
print(result)
"""
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", code, value],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for value in ("left", "right")
    ]

    completed = [process.communicate(timeout=20) for process in processes]
    assert [process.returncode for process in processes] == [0, 0]
    returned = [stdout.splitlines()[-1] for stdout, _stderr in completed]
    cache = json.loads((state_dir / "statusline-probe-cache.json").read_text())
    assert returned[0] == returned[1] == cache["shared"]["val"]
    assert cache["shared"]["val"] in {"left", "right"}
    assert set(cache) == {"shared"}


def test_waiting_probe_uses_transaction_time_to_recognize_the_winner(monkeypatch):
    clock = iter((100.0, 102.0))
    monkeypatch.setattr(probes.time, "time", lambda: next(clock))
    monkeypatch.setattr(probes, "read_json", lambda _path, _default: {})

    def publish_after_another_writer(_path, _default, updater):
        cache = {"shared": {"at": 101.0, "val": "winner"}}
        changed, result = updater(cache)
        assert not changed
        assert cache == {"shared": {"at": 101.0, "val": "winner"}}
        return result

    monkeypatch.setattr(probes, "update_json", publish_after_another_writer)

    assert probes.probe("shared", 60, lambda: "waiting-writer") == "winner"
