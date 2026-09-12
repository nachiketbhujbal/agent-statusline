"""The width-fitting behaviour: fit on one line, else wrap, else truncate."""

import math
import os

import pytest

from agent_statusline import render


def widths(text):
    return [render.vis(line) for line in text.split("\n")]


@pytest.fixture
def wide(monkeypatch):
    monkeypatch.setattr(render, "width", lambda: 200)


@pytest.fixture
def narrow(monkeypatch):
    monkeypatch.setattr(render, "width", lambda: 40)


class TestVis:
    def test_ignores_colour_escapes(self):
        assert render.vis(f"{render.RED}abc{render.R}") == 3

    def test_plain_text_is_its_own_length(self):
        assert render.vis("abcde") == 5

    def test_counts_wide_and_combining_unicode_as_terminal_cells(self):
        assert render.vis("界") == 2
        assert render.vis("e\u0301") == 1
        assert render.vis("A界e\u0301") == 4

    def test_sanitize_preserves_only_package_sgr(self):
        text = f"{render.RED}safe{render.R}\033[38;5;196mvalue"

        cleaned = render.sanitize(text)

        assert render.RED in cleaned
        assert render.R in cleaned
        assert "\033[38;5;196m" not in cleaned
        assert render.ANSI.sub("", cleaned) == "safevalue"

    def test_plain_removes_even_an_exact_package_sgr_from_untrusted_text(self):
        assert render.plain(f"safe{render.RED}value") == "safevalue"

    @pytest.mark.parametrize(
        "control",
        [
            "\n\r\t\0\u202e\u2066",
            "\033[2J",
            "\033]0;title\x07",
            "\033]8;;https://example.invalid\033\\",
            "\033Pprivate\033\\",
        ],
    )
    def test_sanitize_removes_control_and_escape_inputs(self, control):
        cleaned = render.sanitize(f"safe{control}value")

        assert "\033" not in cleaned
        assert "\n" not in cleaned
        assert "\r" not in cleaned
        assert "\t" not in cleaned
        assert "\u202e" not in cleaned
        assert "\u2066" not in cleaned
        assert "safe" in cleaned
        assert "value" in cleaned

    def test_sanitize_discards_a_trailing_malformed_escape(self):
        cleaned = render.sanitize("safevalue\033[31")

        assert cleaned == "safevalue"


class TestWidth:
    def test_positive_columns_environment_wins(self, monkeypatch):
        monkeypatch.setenv("COLUMNS", "99")
        monkeypatch.setattr(
            render.os,
            "get_terminal_size",
            lambda _fd: (_ for _ in ()).throw(AssertionError("terminal queried")),
        )

        assert render.width() == 99

    @pytest.mark.parametrize("columns", ["", "0", "-2", "not-a-number"])
    def test_unusable_environment_uses_terminal(self, monkeypatch, columns):
        monkeypatch.setenv("COLUMNS", columns)
        monkeypatch.setattr(render.os, "get_terminal_size", lambda _fd: os.terminal_size((87, 24)))

        assert render.width() == 87

    def test_unavailable_terminal_uses_fallback(self, monkeypatch):
        monkeypatch.delenv("COLUMNS", raising=False)

        def unavailable(_fd):
            raise OSError("not a terminal")

        monkeypatch.setattr(render.os, "get_terminal_size", unavailable)

        assert render.width() == render.FALLBACK_WIDTH

    def test_zero_width_terminal_uses_fallback(self, monkeypatch):
        monkeypatch.delenv("COLUMNS", raising=False)
        monkeypatch.setattr(render.os, "get_terminal_size", lambda _fd: os.terminal_size((0, 24)))

        assert render.width() == render.FALLBACK_WIDTH


class TestRow:
    def test_fitting_content_stays_on_one_line(self, wide):
        out = render.row("TEST", ["alpha", "beta", "gamma"])
        assert "\n" not in out
        assert "…" not in out

    def test_overflow_wraps_before_it_truncates(self, narrow):
        out = render.row("TEST", ["a" * 20, "b" * 20])
        assert len(out.split("\n")) == 2
        assert "…" not in out, "should wrap, not drop, while a line is spare"

    def test_continuation_is_indented_under_the_label(self, narrow):
        second = render.row("TEST", ["a" * 20, "b" * 20]).split("\n")[1]
        assert second.startswith(render.D), "an SGR prefix prevents host whitespace trimming"
        assert render.ANSI.sub("", second).startswith(" " * render.LABEL)

    def test_truncates_only_after_maxlines(self, narrow):
        out = render.row("TEST", ["a" * 20, "b" * 20, "c" * 20, "d" * 20])
        assert len(out.split("\n")) == render.MAXLINES
        assert out.endswith(f" {render.D}…{render.R}")

    def test_never_exceeds_the_terminal(self, narrow):
        out = render.row("TEST", [f"seg{i}" * 5 for i in range(12)])
        assert max(widths(out)) <= 40

    def test_segments_are_dropped_from_the_end(self, narrow):
        out = render.row("TEST", ["FIRST" * 4, "MIDDLE" * 4, "LAST" * 4])
        assert "FIRST" in out
        assert "LAST" not in out, "least important segment must go first"

    def test_empty_segments_are_skipped(self, wide):
        assert render.row("TEST", ["", None, "only"]).count("only") == 1

    def test_no_segments_yields_no_row(self, wide):
        assert render.row("TEST", []) == ""

    def test_single_oversized_segment_is_clipped_not_overflowed(self, narrow):
        """One segment wider than the window must still not break the layout."""
        out = render.row("TEST", ["x" * 100])
        assert render.vis(out) <= 40
        assert "x" in out

    def test_untrusted_fields_cannot_inject_lines_or_terminal_commands(self, wide):
        out = render.row(
            f"TEST{render.RED}\nFAKE",
            ["safe\r\nFAKE\033[2J\u202evalue"],
            sep=f"\n{render.RED}\033]0;title\x07",
        )

        assert len(out.splitlines()) == 1
        assert "\033[2J" not in out
        assert "\033]" not in out
        assert "\u202e" not in out
        assert out.count(render.RED) == 0

    @pytest.mark.parametrize("columns", [1, 5, 9, 10, 40])
    def test_every_physical_line_fits_even_at_extreme_widths(self, monkeypatch, columns):
        monkeypatch.setattr(render, "width", lambda: columns)

        out = render.row("TEST", ["界" * 100, "e\u0301" * 100, "tail"], maxlines=2)

        assert out
        assert all(render.vis(line) <= columns for line in out.splitlines())

    def test_dropped_marker_is_reserved_inside_the_width(self, narrow):
        out = render.row("TEST", ["a" * 30, "b" * 30, "c" * 30])

        assert out.endswith(f" {render.D}…{render.R}")
        assert max(widths(out)) <= 40


class TestPack:
    def test_reports_when_it_dropped_something(self):
        _, dropped = render.pack(["a" * 30, "b" * 30, "c" * 30], " ", 30, maxlines=2)
        assert dropped is True

    def test_reports_when_nothing_was_dropped(self):
        lines, dropped = render.pack(["a", "b"], " ", 30, maxlines=2)
        assert dropped is False
        assert lines == [["a", "b"]]


class TestUnits:
    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, "0"),
            (999, "999"),
            (1000, "1k"),
            (1420, "1.42k"),
            (515000, "515k"),
            (1000000, "1M"),
            (71900000, "71.9M"),
        ],
    )
    def test_tok(self, n, expected):
        assert render.tok(n) == expected

    @pytest.mark.parametrize(
        "sec,expected",
        [
            (5, "5s"),
            (90, "1m"),
            (3660, "1h01m"),
            (90000, "1d1h"),
        ],
    )
    def test_dur(self, sec, expected):
        assert render.dur(sec) == expected

    def test_dur_clamps_negatives(self):
        assert render.dur(-10) == "0s"

    def test_gb(self):
        assert render.gb(2**30) == "1.0G"
        assert render.gb(5 * 2**20) == "5M"

    def test_formatters_keep_existing_numeric_string_forms(self):
        assert render.tok("1000") == "1k"
        assert render.gb("1073741824") == "1.0G"
        assert render.dur("90") == "1m"
        assert render.vis(render.bar("50", 10)) == 12

    @pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "nan", "Infinity", 10**400])
    def test_formatters_degrade_nonfinite_and_oversized_values(self, value):
        outputs = [render.tok(value), render.gb(value), render.dur(value), render.bar(value)]
        assert all(
            "nan" not in output.lower() and "inf" not in output.lower() for output in outputs
        )

    @pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "not-a-number", 10**400])
    def test_grade_degrades_invalid_values(self, value):
        assert render.grade(value) == render.GRN


class TestGrade:
    def test_thresholds(self):
        assert render.grade(10) == render.GRN
        assert render.grade(60) == render.YEL
        assert render.grade(90) == render.RED


class TestBar:
    def test_is_exactly_width_cells_wide(self):
        assert render.vis(render.bar(50, 10)) == 12  # 10 cells plus [ and ]

    def test_clamps_out_of_range_values(self):
        assert render.vis(render.bar(999, 10)) == 12
        assert render.vis(render.bar(-5, 10)) == 12


class TestClip:
    def test_leaves_short_segments_alone(self):
        assert render.clip("abc", 10) == "abc"

    def test_truncates_to_the_budget(self):
        assert render.vis(render.clip("x" * 100, 20)) == 20

    def test_zero_budget_returns_empty_output(self):
        assert render.clip("visible", 0) == ""

    @pytest.mark.parametrize("budget", [1, 2, 3, 10])
    def test_never_splits_a_wide_character_across_the_budget(self, budget):
        assert render.vis(render.clip("界" * 20, budget)) <= budget

    def test_preserves_colour_escapes_while_counting_only_text(self):
        clipped = render.clip(f"{render.RED}{'x' * 50}{render.R}", 10)
        assert render.vis(clipped) == 10
        assert render.RED in clipped

    def test_always_resets_colour_at_the_cut(self):
        assert render.clip(f"{render.RED}{'x' * 50}", 10).endswith(render.R)

    def test_a_row_with_one_oversized_segment_still_fits(self, monkeypatch):
        monkeypatch.setattr(render, "width", lambda: 40)
        out = render.row("TEST", ["y" * 200])
        assert max(render.vis(ln) for ln in out.split("\n")) <= 40
