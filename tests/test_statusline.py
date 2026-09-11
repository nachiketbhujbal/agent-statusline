"""End-to-end rendering, against the real probes but an isolated state dir."""

import io
import json
import os
import re
import subprocess
import sys

import pytest

from agent_statusline import render, statusline, transcript
from agent_statusline.hooks import context_guard, session_end
from fixture_payload import verify_render_contract

ANSI = re.compile(r"\033\[[0-9;]*m")


def draw(payload, monkeypatch, capsys, cols=200):
    monkeypatch.setattr(render, "width", lambda: cols)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    statusline.main()
    return capsys.readouterr().out.rstrip("\n").split("\n")


def labels(lines):
    """Row labels in the order they were emitted; continuation lines have none."""
    return [
        ln.split()[0] for ln in (ANSI.sub("", x) for x in lines) if ln and not ln.startswith(" ")
    ]


class TestRowOrder:
    def test_committed_fixture_exercises_exact_transcript_backed_contract(
        self, payload, monkeypatch, capsys
    ):
        output = "\n".join(draw(payload, monkeypatch, capsys, cols=240))
        verify_render_contract(output, statusline.ORDER)

    def test_rows_follow_the_declared_order(self, payload, monkeypatch, capsys):
        got = labels(draw(payload, monkeypatch, capsys))
        assert got == [k for k in statusline.ORDER if k in got]

    def test_project_leads_and_model_follows(self, payload, monkeypatch, capsys):
        assert labels(draw(payload, monkeypatch, capsys))[:2] == ["PROJECT", "MODEL"]

    def test_the_declared_order_has_no_duplicates(self):
        assert len(statusline.ORDER) == len(set(statusline.ORDER))

    def test_committed_fixture_is_independent_of_process_cwd(
        self, payload, monkeypatch, capsys, tmp_path
    ):
        unrelated = tmp_path / "unrelated-cwd"
        unrelated.mkdir()
        monkeypatch.chdir(unrelated)
        output = "\n".join(draw(payload, monkeypatch, capsys, cols=240))
        verify_render_contract(output, statusline.ORDER)


class TestWidth:
    @pytest.mark.parametrize("cols", [240, 200, 160, 120, 100, 80, 60, 40])
    def test_no_line_ever_exceeds_the_terminal(self, payload, monkeypatch, capsys, cols):
        lines = draw(payload, monkeypatch, capsys, cols=cols)
        assert max(render.vis(ln) for ln in lines) <= cols

    def test_narrow_terminals_wrap_rather_than_lose_rows(self, payload, monkeypatch, capsys):
        wide = labels(draw(payload, monkeypatch, capsys, cols=240))
        narrow = labels(draw(payload, monkeypatch, capsys, cols=70))
        assert narrow == wide, "every row must survive; only segments are dropped"

    def test_a_row_never_exceeds_maxlines(self, payload, monkeypatch, capsys):
        lines = draw(payload, monkeypatch, capsys, cols=60)
        run = 0
        for line in lines:
            visible = ANSI.sub("", line)
            run = run + 1 if visible.startswith(" " * render.LABEL) else 0
            assert run < render.MAXLINES


class TestContent:
    def test_model_and_effort_are_shown(self, payload, monkeypatch, capsys):
        assert "Synthetic Opus" in ANSI.sub("", draw(payload, monkeypatch, capsys)[1])

    def test_cost_comes_straight_from_the_payload(self, payload, monkeypatch, capsys):
        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))
        assert "$1.25" in out, "cost must be passed through, never recomputed"

    def test_spanning_legacy_cost_renders_as_a_lower_bound(self, payload, monkeypatch, capsys):
        now = 1_800_000_000
        monkeypatch.setattr(statusline.time, "time", lambda: now)
        statusline.ledger.save(
            {
                "sessions": {
                    "legacy": {
                        "cost": 10.0,
                        "started": statusline.ledger.iso(now - 2 * 86400),
                        "updated": statusline.ledger.iso(now),
                    }
                }
            }
        )

        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))

        assert "24h ≥$1.25" in out
        assert "7d $11.25" in out
        assert "30d $11.25" in out

    def test_cost_attribution_receives_assistant_time_and_wall_duration(
        self, payload, monkeypatch, capsys
    ):
        seen = {}
        last_ts = "2026-09-11T03:00:00Z"
        monkeypatch.setattr(statusline, "transcript_totals", lambda _path: _totals(last_ts=last_ts))

        def fake_ledger_update(*_args, **kwargs):
            seen.update(kwargs)
            return {
                "session": 1.25,
                "base": 0.0,
                "runs": 1,
                "d1": 1.25,
                "d1_complete": True,
                "d7": 1.25,
                "d7_complete": True,
                "d30": 1.25,
                "d30_complete": True,
                "last5": 1.25,
                "all": 1.25,
                "convos": 1,
                "n": 1,
                "forks": 0,
            }

        monkeypatch.setattr(statusline, "ledger_update", fake_ledger_update)

        draw(payload, monkeypatch, capsys)

        assert seen["accrued_at"] == last_ts
        assert seen["duration"] == payload["cost"]["total_duration_ms"] / 1000

    @pytest.mark.parametrize("duration", [None, "invalid", -1, 0, 10**15])
    def test_cost_attribution_rejects_unusable_session_duration(
        self, payload, monkeypatch, capsys, duration
    ):
        seen = {}
        payload["cost"]["total_duration_ms"] = duration

        def fake_ledger_update(*_args, **kwargs):
            seen.update(kwargs)
            return {
                "session": 1.25,
                "base": 0.0,
                "runs": 1,
                "d1": 0.0,
                "d1_complete": False,
                "d7": 0.0,
                "d7_complete": False,
                "d30": 0.0,
                "d30_complete": False,
                "last5": 1.25,
                "all": 1.25,
                "convos": 1,
                "n": 1,
                "forks": 0,
            }

        monkeypatch.setattr(statusline, "ledger_update", fake_ledger_update)

        draw(payload, monkeypatch, capsys)

        assert seen["duration"] is None

    def test_permission_mode_uses_claude_codes_own_colours(self):
        assert statusline.MODES["auto"][0] == render.YEL
        assert statusline.MODES["plan"][0] == render.CYN
        assert statusline.MODES["bypassPermissions"][0] == render.RED

    def test_five_minute_cache_ttl_is_flagged_red(self, payload, monkeypatch, capsys):
        """The 5m bucket means the account dropped to a short TTL: the real signal."""
        monkeypatch.setattr(statusline, "transcript_totals", lambda _p: _totals(last_bucket="5m"))
        out = "\n".join(draw(payload, monkeypatch, capsys))
        assert f"{render.RED}{render.B}5m" in out

    def test_one_hour_cache_ttl_is_not_flagged(self, payload, monkeypatch, capsys):
        monkeypatch.setattr(statusline, "transcript_totals", lambda _p: _totals(last_bucket="1h"))
        out = "\n".join(draw(payload, monkeypatch, capsys))
        assert f"{render.GRN}{render.B}1h" in out


class TestRobustness:
    def test_empty_payload_does_not_crash(self, monkeypatch, capsys):
        assert draw({}, monkeypatch, capsys)

    def test_malformed_stdin_degrades_to_a_stub(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        statusline.main()
        assert "claude" in ANSI.sub("", capsys.readouterr().out)

    @pytest.mark.parametrize("state_shape", ["file", "child-of-file"])
    def test_unusable_state_root_does_not_abort_fresh_process(self, tmp_path, payload, state_shape):
        blocker = tmp_path / "blocked"
        blocker.write_text("sentinel")
        state_root = blocker if state_shape == "file" else blocker / "state"
        env = dict(os.environ)
        env["AGENT_STATUSLINE_STATE"] = str(state_root)
        env["HOME"] = str(tmp_path / "home")
        env["COLUMNS"] = "200"
        source = os.path.abspath("src")
        env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [sys.executable, "-m", "agent_statusline.statusline"],
            input=json.dumps(payload),
            env=env,
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=20,
        )

        assert result.returncode == 0, result.stderr
        assert "PROJECT" in ANSI.sub("", result.stdout)
        assert blocker.read_text() == "sentinel"

    def test_transcript_state_failure_does_not_abort_render(
        self, tmp_path, payload, monkeypatch, capsys
    ):
        transcript_path = tmp_path / "session.jsonl"
        transcript_path.write_text('{"type":"assistant","message":{"usage":{"input_tokens":5}}}\n')
        payload["transcript_path"] = str(transcript_path)

        def fail_state(_path, _default, _updater):
            raise PermissionError("read-only transcript state")

        monkeypatch.setattr(transcript, "update_json", fail_state)

        assert "PROJECT" in labels(draw(payload, monkeypatch, capsys))

    @pytest.mark.parametrize("payload", [[], ["not a payload"], "scalar", 17, None])
    def test_json_non_object_payload_degrades_to_a_stub(self, payload, monkeypatch, capsys):
        assert ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys))) == "claude"

    def test_missing_rate_limits_are_simply_absent(self, payload, monkeypatch, capsys):
        payload.pop("rate_limits")
        assert "USAGE" not in labels(draw(payload, monkeypatch, capsys))

    def test_process_probe_is_scoped_to_each_session(self, payload, monkeypatch, capsys):
        keys = []

        def capture(key, _ttl, fn):
            if key.startswith("procs:"):
                keys.append(key)
                return fn()
            return {}

        snapshots = iter(
            [
                {"mine_pid": 101, "mine_rss": 1024, "mine_procs": 1, "all_rss": 1024},
                {"mine_pid": 202, "mine_rss": 2048, "mine_procs": 2, "all_rss": 4096},
            ]
        )
        monkeypatch.setattr(statusline.pr, "probe", capture)
        monkeypatch.setattr(statusline.pr, "processes", lambda: next(snapshots))

        payload["session_id"] = "session-a"
        first = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))
        payload["session_id"] = "session-b"
        second = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))

        assert keys == ["procs:session:session-a", "procs:session:session-b"]
        assert "pid 101" in first
        assert "pid 202" in second

    def test_missing_process_session_uses_noncolliding_parent_scope(
        self, payload, monkeypatch, capsys
    ):
        keys = []

        def capture(key, _ttl, _fn):
            if key.startswith("procs:"):
                keys.append(key)
            return {}

        monkeypatch.setattr(statusline.pr, "probe", capture)
        monkeypatch.setattr(statusline.os, "getppid", lambda: 4242)

        payload.pop("session_id")
        draw(payload, monkeypatch, capsys)
        draw(payload, monkeypatch, capsys)
        payload["session_id"] = "parent:4242"
        draw(payload, monkeypatch, capsys)

        assert keys == [
            "procs:parent:4242",
            "procs:parent:4242",
            "procs:session:parent:4242",
        ]

    def test_empty_process_session_remains_an_opaque_session_scope(
        self, payload, monkeypatch, capsys
    ):
        keys = []

        def capture(key, _ttl, _fn):
            if key.startswith("procs:"):
                keys.append(key)
            return {}

        monkeypatch.setattr(statusline.pr, "probe", capture)
        payload["session_id"] = ""

        draw(payload, monkeypatch, capsys)

        assert keys == ["procs:session:"]

    def test_malformed_numeric_payload_values_use_safe_defaults(self, payload, monkeypatch, capsys):
        payload["context_window"]["context_window_size"] = float("inf")
        payload["context_window"]["used_percentage"] = "not-a-number"
        payload["context_window"]["current_usage"]["input_tokens"] = float("nan")
        payload["rate_limits"]["five_hour"]["used_percentage"] = float("-inf")
        payload["rate_limits"]["five_hour"]["resets_at"] = 10**15
        payload["cost"].update(
            {
                "total_cost_usd": float("nan"),
                "total_duration_ms": float("inf"),
                "total_api_duration_ms": "invalid",
                "total_lines_added": float("-inf"),
                "total_lines_removed": "invalid",
            }
        )

        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys))).lower()

        assert "nan" not in out
        assert "inf" not in out
        assert "context" in out
        assert "timing" in out
        assert "cost" in out

    def test_non_mapping_current_usage_is_treated_as_empty(self, payload, monkeypatch, capsys):
        payload["context_window"]["current_usage"] = ["invalid"]

        assert "CONTEXT" in labels(draw(payload, monkeypatch, capsys))

    @pytest.mark.parametrize("value", [True, 17, 1.5, ["invalid"], {"invalid": True}])
    @pytest.mark.parametrize(
        "path",
        [
            ("session_id",),
            ("transcript_path",),
            ("permission_mode",),
            ("workspace", "current_dir"),
            ("workspace", "project_dir"),
            ("workspace", "added_dirs"),
        ],
    )
    def test_malformed_scalar_and_container_fields_degrade(
        self, payload, monkeypatch, capsys, path, value
    ):
        target = payload
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))

        assert "PROJECT" in out
        assert "MODEL" in out

    def test_fractional_rate_limit_percentage_is_floored(self, payload, monkeypatch, capsys):
        payload["rate_limits"]["five_hour"]["used_percentage"] = 14.5

        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))
        allowance = out.split("5h [", 1)[1].split("@", 1)[0]

        assert "5h [" in out
        assert " 14%" in allowance
        assert "14.5%" not in allowance
        assert "%/h" in out, "the burn-rate decimal remains present"

    def test_exact_package_sgr_in_untrusted_payload_text_is_removed(
        self, payload, monkeypatch, capsys
    ):
        payload["model"]["display_name"] = f"safe{render.RED}model"
        payload["session_name"] = f"safe{render.RED}session"

        out = "\n".join(draw(payload, monkeypatch, capsys))

        assert f"safe{render.RED}model" not in out
        assert f"safe{render.RED}session" not in out
        assert "safemodel" in ANSI.sub("", out)
        assert "safesession" in ANSI.sub("", out)

    @pytest.mark.parametrize(
        ("percentage", "shown"),
        [(99.5, " 99%"), (99.999, " 99%"), (100.0, "100%"), (100.1, "100%")],
    )
    def test_allowance_floor_never_claims_early_exhaustion(
        self, payload, monkeypatch, capsys, percentage, shown
    ):
        payload["rate_limits"]["five_hour"]["used_percentage"] = percentage

        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))

        assert shown in out
        assert ("OVERAGE" in out) is (percentage >= 100)

    def test_nested_git_display_does_not_rebind_disk_probe(
        self, payload, monkeypatch, capsys, tmp_path
    ):
        child = tmp_path / "synthetic-child"
        (child / ".git").mkdir(parents=True)
        payload["cwd"] = str(tmp_path)
        payload["workspace"]["current_dir"] = str(tmp_path)
        payload["workspace"]["project_dir"] = str(tmp_path)
        keys = []

        def probe(key, _ttl, _function):
            keys.append(key)
            if key == f"git:{tmp_path}":
                return None
            if key == f"git:{child}":
                return {
                    "branch": "synthetic",
                    "dirty": False,
                    "ahead": 0,
                    "behind": 0,
                    "upstream": None,
                    "worktree": False,
                    "stash": 0,
                }
            return {}

        monkeypatch.setattr(statusline.pr, "probe", probe)

        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))

        assert "↳synthetic-child synthetic" in out
        assert f"disk:{tmp_path}" in keys
        assert f"disk:{child}" not in keys

    def test_absent_cost_remains_distinct_from_zero(self, payload, monkeypatch, capsys):
        payload["cost"].pop("total_cost_usd")
        seen = {}

        def fake_ledger_update(_sid, cost, *_args, **_kwargs):
            seen["cost"] = cost
            return {
                "session": 0.0,
                "base": 0.0,
                "runs": 1,
                "d1": 0.0,
                "d1_complete": False,
                "d7": 0.0,
                "d7_complete": False,
                "d30": 0.0,
                "d30_complete": False,
                "last5": 0.0,
                "all": 0.0,
                "convos": 0,
                "n": 0,
                "forks": 0,
            }

        monkeypatch.setattr(statusline, "ledger_update", fake_ledger_update)
        draw(payload, monkeypatch, capsys)

        assert seen["cost"] is None

    def test_cached_non_string_ledger_root_does_not_break_other_sessions(self, monkeypatch):
        data = {
            "sessions": {
                "prior": {
                    "cost": 1.0,
                    "updated": statusline.ledger.iso(),
                    "root": ["invalid"],
                }
            }
        }

        def fake_update(updater):
            return updater(data)[1]

        monkeypatch.setattr(statusline.ledger, "update", fake_update)

        aggregate = statusline.ledger_update("current", None, "project", "session")

        assert aggregate["n"] == 1
        assert aggregate["convos"] == 1

    def test_cached_non_string_ledger_root_is_removed_when_session_updates(self, monkeypatch):
        data = {
            "sessions": {
                "prior": {
                    "cost": 1.0,
                    "updated": statusline.ledger.iso(),
                    "root": ["invalid"],
                }
            }
        }
        saved = {}

        def fake_update(updater):
            changed, result = updater(data)
            if changed:
                saved["data"] = data
            return result

        monkeypatch.setattr(statusline.ledger, "update", fake_update)

        statusline.ledger_update("prior", 2.0, "project", "session")

        assert "root" not in saved["data"]["sessions"]["prior"]

    def test_invalid_transcript_permission_falls_back_to_valid_payload(
        self, payload, monkeypatch, capsys
    ):
        payload["permission_mode"] = "acceptEdits"
        monkeypatch.setattr(statusline, "transcript_totals", lambda _path: _totals(perm=["plan"]))

        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))

        assert "accept edits" in out

    def test_malformed_transcript_numbers_do_not_remove_rows(self, payload, monkeypatch, capsys):
        monkeypatch.setattr(
            statusline,
            "transcript_totals",
            lambda _path: _totals(
                cr=float("nan"),
                cw=float("inf"),
                out="invalid",
                think=True,
                turns="invalid",
                b1h=float("inf"),
                b5m="invalid",
                durs=[float("nan"), 1200],
            ),
        )

        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys))).lower()

        assert "nan" not in out
        assert "inf" not in out
        assert "context" in out
        assert "timing" in out


class TestSerializedRuntimeState:
    def test_payload_is_published_through_storage(self, monkeypatch, capsys):
        seen = {}
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
        monkeypatch.setattr(
            statusline,
            "write_text",
            lambda path, text: seen.update(path=path, text=text),
        )

        statusline.main()

        assert seen == {"path": statusline.PAYLOAD, "text": "not json"}
        assert "claude" in ANSI.sub("", capsys.readouterr().out)

    def test_payload_storage_failure_does_not_remove_fallback(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.stdin", io.StringIO("not json"))

        def fail_write(_path, _text):
            raise OSError("state unavailable")

        monkeypatch.setattr(statusline, "write_text", fail_write)

        statusline.main()

        assert "claude" in ANSI.sub("", capsys.readouterr().out)

    def test_rate_history_is_appended_through_storage(self, monkeypatch):
        seen = {}

        def fake_append(path, record, keys, **options):
            seen.update(path=path, record=record, keys=keys, options=options)
            return True

        monkeypatch.setattr(statusline, "append_json_if_changed", fake_append)

        statusline.rl_log(
            {"used_percentage": 15, "resets_at": 1_700_000_000},
            {"used_percentage": 40, "resets_at": 1_800_000_000},
        )

        assert seen["path"] == statusline.RLHIST
        assert seen["keys"] == ("5h", "5h_reset", "7d", "7d_reset")
        assert seen["options"] == {"max_bytes": statusline.RATE_HISTORY_MAX_BYTES}
        assert {key: seen["record"][key] for key in seen["keys"]} == {
            "5h": 15.0,
            "5h_reset": 1_700_000_000.0,
            "7d": 40.0,
            "7d_reset": 1_800_000_000.0,
        }
        assert "at" in seen["record"]

    def test_ledger_storage_failure_preserves_a_renderable_aggregate(self, monkeypatch):
        def fail_update(_updater):
            raise OSError("state unavailable")

        monkeypatch.setattr(statusline.ledger, "update", fail_update)

        aggregate = statusline.ledger_update(
            "session-1",
            2.5,
            "project",
            "name",
            root="conversation-1",
            pid=100,
            duration=600,
        )

        assert aggregate["session"] == 2.5
        assert aggregate["all"] == 2.5
        assert aggregate["n"] == 1
        assert aggregate["convos"] == 1
        assert aggregate["d1"] == 2.5
        assert aggregate["d7"] == 2.5
        assert aggregate["d30"] == 2.5
        assert not any(aggregate[key + "_complete"] for key in statusline.ledger.COST_WINDOWS)

    def test_empty_session_identifier_remains_a_valid_opaque_journal_key(self, monkeypatch):
        now = 1_800_000_000
        data = {"sessions": {}}

        monkeypatch.setattr(statusline.time, "time", lambda: now)
        monkeypatch.setattr(statusline.ledger, "update", lambda updater: updater(data)[1])

        aggregate = statusline.ledger_update("", 1.25, "project", "name", duration=600)

        assert set(data["sessions"]) == {""}
        assert [event["session"] for event in data["cost_events"]] == [""]
        assert aggregate["d1"] == 1.25
        assert aggregate["d1_complete"]

    @pytest.mark.parametrize("duration", [None, "invalid", -1, 0, 10**12])
    def test_unusable_duration_keeps_a_first_sighting_unattributed(self, monkeypatch, duration):
        now = 1_800_000_000
        data = {"sessions": {}}

        monkeypatch.setattr(statusline.time, "time", lambda: now)
        monkeypatch.setattr(statusline.ledger, "update", lambda updater: updater(data)[1])

        aggregate = statusline.ledger_update(
            "session-1", 100.0, "project", "name", duration=duration
        )

        assert data["cost_events"][0]["started_at"] is None
        assert aggregate["session"] == 100.0
        assert aggregate["all"] == 100.0
        assert aggregate["d1"] == 0.0
        assert aggregate["d1_unattributed"] == 100.0
        assert not any(aggregate[key + "_complete"] for key in statusline.ledger.COST_WINDOWS)

    def test_ledger_publish_failure_preserves_computed_exact_money(self, monkeypatch):
        stamp = statusline.ledger.iso()
        data = {
            "sessions": {
                "prior": {
                    "cost": 5.0,
                    "updated": stamp,
                    "state": "closed",
                    "root": "conversation-prior",
                },
                "session-1": {
                    "cost": 10.0,
                    "cost_base": 0.0,
                    "cost_run": 10.0,
                    "runs": 1,
                    "pid": 100,
                    "updated": stamp,
                    "state": "live",
                    "root": "conversation-current",
                },
            }
        }
        seen = {}

        def fail_after_update(updater):
            changed, result = updater(data)
            assert changed
            seen["computed"] = result
            raise OSError("publication failed")

        monkeypatch.setattr(statusline.ledger, "update", fail_after_update)

        aggregate = statusline.ledger_update(
            "session-1", 2.0, "project", "name", root="conversation-current", pid=200
        )

        assert aggregate == seen["computed"]
        assert aggregate["session"] == 12.0
        assert aggregate["base"] == 10.0
        assert aggregate["runs"] == 2
        assert aggregate["all"] == 17.0
        assert aggregate["last5"] == 17.0
        assert aggregate["d1"] == 2.0
        assert aggregate["d7"] == 2.0
        assert aggregate["d30"] == 2.0
        assert aggregate["d30_unattributed"] == 15.0
        assert not aggregate["d30_complete"]

    def test_existing_lifetime_is_seeded_before_a_new_delta_is_attributed(self, monkeypatch):
        now = 1_800_000_000
        accrued = statusline.ledger.iso(now - 60)
        data = {
            "sessions": {
                "session-1": {
                    "cost": 10.0,
                    "cost_base": 0.0,
                    "cost_run": 10.0,
                    "runs": 1,
                    "pid": 100,
                    "started": statusline.ledger.iso(now - 2 * 86400),
                    "updated": statusline.ledger.iso(now - 120),
                    "state": "live",
                }
            }
        }

        monkeypatch.setattr(statusline.time, "time", lambda: now)
        monkeypatch.setattr(statusline.ledger, "update", lambda updater: updater(data)[1])

        aggregate = statusline.ledger_update(
            "session-1", 12.0, "project", "name", pid=100, accrued_at=accrued
        )

        assert [event["seed"] for event in data["cost_events"]] == [True, False]
        assert data["cost_events"][0]["delta"] == 10.0
        assert data["cost_events"][1]["delta"] == 2.0
        assert data["cost_events"][1]["accrued_at"] == accrued
        assert aggregate["session"] == 12.0
        assert aggregate["d1"] == 2.0
        assert aggregate["d1_unattributed"] == 10.0
        assert not aggregate["d1_complete"]

    def test_concurrent_statusline_writers_preserve_every_session(self, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        env = dict(os.environ)
        env["AGENT_STATUSLINE_STATE"] = str(state_dir)
        env["HOME"] = str(tmp_path / "home")
        source = os.path.abspath("src")
        env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
        code = r"""
import sys
from agent_statusline.statusline import ledger_update

number = int(sys.argv[1])
ledger_update(
    f"session-{number}",
    float(number + 1),
    "project",
    f"writer-{number}",
    root=f"conversation-{number}",
    pid=number + 100,
)
"""
        processes = [
            subprocess.Popen([sys.executable, "-c", code, str(number)], env=env)
            for number in range(8)
        ]

        assert [process.wait(timeout=20) for process in processes] == [0] * 8
        sessions = json.loads((state_dir / "cost-ledger.json").read_text())["sessions"]
        assert set(sessions) == {f"session-{number}" for number in range(8)}
        assert sum(row["cost"] for row in sessions.values()) == 36.0
        events = json.loads((state_dir / "cost-ledger.json").read_text())["cost_events"]
        assert len(events) == 8
        assert all(event["seed"] for event in events)

    def test_concurrent_rate_history_writers_deduplicate_same_facts(self, tmp_path):
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        env = dict(os.environ)
        env["AGENT_STATUSLINE_STATE"] = str(state_dir)
        env["HOME"] = str(tmp_path / "home")
        source = os.path.abspath("src")
        env["PYTHONPATH"] = source + os.pathsep + env.get("PYTHONPATH", "")
        code = r"""
from agent_statusline.statusline import rl_log

rl_log(
    {"used_percentage": 15, "resets_at": 1700000000},
    {"used_percentage": 40, "resets_at": 1800000000},
)
"""
        processes = [subprocess.Popen([sys.executable, "-c", code], env=env) for _ in range(8)]

        assert [process.wait(timeout=20) for process in processes] == [0] * 8
        lines = (state_dir / "rate-limit-history.jsonl").read_text().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["5h"] == 15.0

    def test_context_guard_uses_storage_for_payload_and_lastrun(self, monkeypatch):
        seen = {}
        monkeypatch.setattr(
            context_guard,
            "read_json",
            lambda path, default: {
                "context_window": {"context_window_size": 200_000},
                "path": path,
                "default": default,
            },
        )

        assert context_guard.window_size() == 200_000

        monkeypatch.setattr("sys.stdin", io.StringIO('{"session_id":"session-1"}'))
        monkeypatch.setattr(context_guard, "window_size", lambda: 0)
        monkeypatch.setattr(
            context_guard,
            "write_text",
            lambda path, text: seen.update(path=path, record=json.loads(text)),
        )

        assert context_guard.main() == 0
        assert os.fspath(seen["path"]).endswith("hook-lastrun.json")
        assert seen["record"]["hook"] == "UserPromptSubmit"
        assert seen["record"]["session"] == "session-1"

    def test_context_guard_read_failure_keeps_default_window(self, monkeypatch):
        def fail_read(_path, _default):
            raise OSError("state unavailable")

        monkeypatch.setattr(context_guard, "read_json", fail_read)

        assert context_guard.window_size() == 1_000_000

    def test_session_end_creates_and_closes_through_one_ledger_call(self, monkeypatch):
        seen = {}
        monkeypatch.setattr(
            "sys.stdin",
            io.StringIO(
                json.dumps(
                    {
                        "session_id": "session-1",
                        "reason": "logout",
                        "transcript_path": "/synthetic/transcript.jsonl",
                    }
                )
            ),
        )

        def fail_legacy_call(*_args, **_kwargs):
            raise AssertionError("legacy load/save path must not run")

        def fake_close(sid, reason, transcript=None, when=None, create=False):
            seen.update(
                sid=sid,
                reason=reason,
                transcript=transcript,
                when=when,
                create=create,
            )
            return {"state": "closed"}

        monkeypatch.setattr(session_end.ledger, "load", fail_legacy_call)
        monkeypatch.setattr(session_end.ledger, "save", fail_legacy_call)
        monkeypatch.setattr(session_end.ledger, "close_session", fake_close)

        assert session_end.main() == 0
        assert seen == {
            "sid": "session-1",
            "reason": "logout",
            "transcript": "/synthetic/transcript.jsonl",
            "when": None,
            "create": True,
        }


def _totals(**over):
    from agent_statusline.transcript import _blank

    tot = _blank()
    tot.update(
        {"cr": 1000, "cw": 100, "in": 10, "out": 50, "turns": 2, "last_ts": "2099-01-01T00:00:00Z"}
    )
    tot.update(over)
    return tot
