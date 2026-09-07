"""End-to-end rendering, against the real probes but an isolated state dir."""

import io
import json
import os
import re
import subprocess
import sys

import pytest

from agent_statusline import render, statusline
from agent_statusline.hooks import context_guard, session_end

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
    def test_rows_follow_the_declared_order(self, payload, monkeypatch, capsys):
        got = labels(draw(payload, monkeypatch, capsys))
        assert got == [k for k in statusline.ORDER if k in got]

    def test_project_leads_and_model_follows(self, payload, monkeypatch, capsys):
        assert labels(draw(payload, monkeypatch, capsys))[:2] == ["PROJECT", "MODEL"]

    def test_the_declared_order_has_no_duplicates(self):
        assert len(statusline.ORDER) == len(set(statusline.ORDER))


class TestWidth:
    @pytest.mark.parametrize("cols", [240, 200, 160, 120, 100, 80, 60, 40])
    def test_no_line_ever_exceeds_the_terminal(self, payload, monkeypatch, capsys, cols):
        lines = draw(payload, monkeypatch, capsys, cols=cols)
        assert max(len(ANSI.sub("", ln)) for ln in lines) <= cols

    def test_narrow_terminals_wrap_rather_than_lose_rows(self, payload, monkeypatch, capsys):
        wide = labels(draw(payload, monkeypatch, capsys, cols=240))
        narrow = labels(draw(payload, monkeypatch, capsys, cols=70))
        assert narrow == wide, "every row must survive; only segments are dropped"

    def test_a_row_never_exceeds_maxlines(self, payload, monkeypatch, capsys):
        lines = draw(payload, monkeypatch, capsys, cols=60)
        run = 0
        for line in lines:
            run = run + 1 if line.startswith(" " * render.LABEL) else 0
            assert run < render.MAXLINES


class TestContent:
    def test_model_and_effort_are_shown(self, payload, monkeypatch, capsys):
        assert "Opus 5" in ANSI.sub("", draw(payload, monkeypatch, capsys)[1])

    def test_cost_comes_straight_from_the_payload(self, payload, monkeypatch, capsys):
        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))
        assert "$1.25" in out, "cost must be passed through, never recomputed"

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

    @pytest.mark.parametrize("payload", [[], ["not a payload"], "scalar", 17, None])
    def test_json_non_object_payload_degrades_to_a_stub(self, payload, monkeypatch, capsys):
        assert ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys))) == "claude"

    def test_missing_rate_limits_are_simply_absent(self, payload, monkeypatch, capsys):
        payload.pop("rate_limits")
        assert "USAGE" not in labels(draw(payload, monkeypatch, capsys))

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

    def test_fractional_rate_limit_percentage_is_preserved(self, payload, monkeypatch, capsys):
        payload["rate_limits"]["five_hour"]["used_percentage"] = 14.5

        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))

        assert "14.5%" in out

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
                "d7": 0.0,
                "d30": 0.0,
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

        def fake_append(path, record, keys):
            seen.update(path=path, record=record, keys=keys)
            return True

        monkeypatch.setattr(statusline, "append_json_if_changed", fake_append)

        statusline.rl_log(
            {"used_percentage": 15, "resets_at": 1_700_000_000},
            {"used_percentage": 40, "resets_at": 1_800_000_000},
        )

        assert seen["path"] == statusline.RLHIST
        assert seen["keys"] == ("5h", "5h_reset", "7d", "7d_reset")
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
            "session-1", 2.5, "project", "name", root="conversation-1", pid=100
        )

        assert aggregate["session"] == 2.5
        assert aggregate["all"] == 2.5
        assert aggregate["n"] == 1
        assert aggregate["convos"] == 1

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
        assert aggregate["d1"] == 17.0
        assert aggregate["d7"] == 17.0
        assert aggregate["d30"] == 17.0

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
        assert seen["path"].endswith("hook-lastrun.json")
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
