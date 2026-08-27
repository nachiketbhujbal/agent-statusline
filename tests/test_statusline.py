"""End-to-end rendering, against the real probes but an isolated state dir."""

import io
import json
import re
import time

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


def _totals(**over):
    from agent_statusline.transcript import _blank

    tot = _blank()
    tot.update(
        {"cr": 1000, "cw": 100, "in": 10, "out": 50, "turns": 2, "last_ts": "2099-01-01T00:00:00Z"}
    )
    tot.update(over)
    return tot
