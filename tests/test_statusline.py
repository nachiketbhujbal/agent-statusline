"""End-to-end rendering, against the real probes but an isolated state dir."""

import io
import json
import re
import stat
import time
from pathlib import Path

import pytest

from agent_statusline import render, statusline

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
    def test_committed_fixture_exercises_every_approved_row(self, payload, monkeypatch, capsys):
        assert labels(draw(payload, monkeypatch, capsys)) == statusline.ORDER

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
        monkeypatch.chdir(tmp_path)
        assert labels(draw(payload, monkeypatch, capsys)) == statusline.ORDER


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
            run = run + 1 if line.startswith(" " * render.LABEL) else 0
            assert run < render.MAXLINES


class TestContent:
    def test_model_and_effort_are_shown(self, payload, monkeypatch, capsys):
        assert "Synthetic Opus" in ANSI.sub("", draw(payload, monkeypatch, capsys)[1])

    def test_cost_comes_straight_from_the_payload(self, payload, monkeypatch, capsys):
        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))
        assert "$1.25" in out, "cost must be passed through, never recomputed"

    def test_usage_exercises_projection_and_reset_clock(self, payload, monkeypatch, capsys):
        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))
        assert "%/h" in out
        assert "reset " in out

    def test_nested_git_display_does_not_rebind_disk_probe(
        self, payload, monkeypatch, capsys, tmp_path
    ):
        child = tmp_path / "synthetic-child"
        (child / ".git").mkdir(parents=True)
        payload["cwd"] = str(tmp_path)
        payload["workspace"]["current_dir"] = str(tmp_path)
        payload["workspace"]["project_dir"] = str(tmp_path)
        keys = []

        def probe(key, _ttl, function):
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
        draw(payload, monkeypatch, capsys)

        assert f"disk:{tmp_path}" in keys
        assert f"disk:{child}" not in keys

    def test_spanning_legacy_cost_is_marked_as_a_lower_bound(self, payload, monkeypatch, capsys):
        from agent_statusline import ledger

        now = time.time()
        ledger.save(
            {
                "sessions": {
                    "legacy": {
                        "cost": 10.0,
                        "started": ledger.iso(now - 2 * 86400),
                        "updated": ledger.iso(now),
                    }
                }
            }
        )
        out = ANSI.sub("", "\n".join(draw(payload, monkeypatch, capsys)))
        assert "24h ≥$1.25" in out
        assert "7d $11.25" in out
        assert "30d $11.25" in out

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

    def test_missing_rate_limits_are_simply_absent(self, payload, monkeypatch, capsys):
        payload.pop("rate_limits")
        assert "USAGE" not in labels(draw(payload, monkeypatch, capsys))

    def test_unexpected_failure_leaves_only_a_private_safe_breadcrumb(self, monkeypatch):
        from agent_statusline import diagnostics

        breadcrumb = Path(diagnostics.LAST_RENDER_ERROR)
        breadcrumb.unlink(missing_ok=True)

        def fail():
            raise RuntimeError("sensitive /private/example/path and payload text")

        monkeypatch.setattr(statusline, "_render", fail)
        with pytest.raises(RuntimeError, match="sensitive"):
            statusline.main()

        record = json.loads(breadcrumb.read_text())
        assert set(record) == {"schema", "occurred_at", "phase", "error_type"}
        assert record["schema"] == 1
        assert record["phase"] == "render"
        assert record["error_type"] == "RuntimeError"
        assert "sensitive" not in breadcrumb.read_text()
        assert "private" not in breadcrumb.read_text()
        assert stat.S_IMODE(breadcrumb.stat().st_mode) == 0o600

    def test_breadcrumb_failure_never_masks_the_render_failure(self, monkeypatch):
        from agent_statusline import diagnostics

        def fail_render():
            raise ValueError("original")

        def fail_record(_error):
            raise OSError("state unavailable")

        monkeypatch.setattr(statusline, "_render", fail_render)
        monkeypatch.setattr(diagnostics, "record_render_failure", fail_record)
        with pytest.raises(ValueError, match="original"):
            statusline.main()

    def test_process_probe_is_scoped_to_each_concurrent_session(self, payload, monkeypatch, capsys):
        keys = []
        real_probe = statusline.pr.probe

        def capture(key, ttl, fn):
            if key.startswith("procs:"):
                keys.append(key)
                return {}
            return real_probe(key, ttl, fn)

        monkeypatch.setattr(statusline.pr, "probe", capture)
        payload["session_id"] = "session-a"
        draw(payload, monkeypatch, capsys)
        payload["session_id"] = "session-b"
        draw(payload, monkeypatch, capsys)

        assert keys == ["procs:session-a", "procs:session-b"]


def _totals(**over):
    from agent_statusline.transcript import _blank

    tot = _blank()
    tot.update(
        {"cr": 1000, "cw": 100, "in": 10, "out": 50, "turns": 2, "last_ts": "2099-01-01T00:00:00Z"}
    )
    tot.update(over)
    return tot
