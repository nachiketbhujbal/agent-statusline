"""Probe caching, isolation, and bounded retention."""

import pytest

from agent_statusline import probes
from agent_statusline.storage import read_json, update_json


@pytest.fixture(autouse=True)
def empty_probe_cache():
    update_json(probes.STATE, {}, lambda current: (True, current.clear()))


def test_independent_process_scopes_do_not_share_a_cached_result():
    calls = []

    def result(pid):
        calls.append(pid)
        return {"mine_pid": pid}

    assert probes.probe("procs:session-a", 8, lambda: result(101))["mine_pid"] == 101
    assert probes.probe("procs:session-b", 8, lambda: result(202))["mine_pid"] == 202
    assert probes.probe("procs:session-a", 8, lambda: result(303))["mine_pid"] == 101
    assert calls == [101, 202]


def test_probe_cache_prunes_stale_and_excess_entries(monkeypatch):
    now = 2_000_000_000.0
    monkeypatch.setattr(probes.time, "time", lambda: now)
    rows = {
        "stale": {"at": now - probes.MAX_CACHE_AGE_S - 1, "val": 1},
        **{
            f"recent:{index}": {"at": now - index, "val": index}
            for index in range(probes.MAX_CACHE_ENTRIES + 10)
        },
        "malformed": "not-a-cache-row",
    }
    update_json(probes.STATE, {}, lambda current: (True, current.update(rows)))

    probes.probe("new", 0, lambda: 42)

    cached = read_json(probes.STATE, {})
    assert "stale" not in cached
    assert "new" in cached
    assert len(cached) == probes.MAX_CACHE_ENTRIES
    assert min(row["at"] for row in cached.values()) >= now - probes.MAX_CACHE_ENTRIES


def test_malformed_current_probe_row_is_replaced():
    update_json(probes.STATE, {}, lambda current: (True, current.update({"bad": []})))

    assert probes.probe("bad", 8, lambda: "recovered") == "recovered"
    assert read_json(probes.STATE, {})["bad"]["val"] == "recovered"
