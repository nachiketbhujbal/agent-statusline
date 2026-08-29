"""Characterization and safety tests for host numeric coercion."""

import math

import pytest

from agent_statusline.coerce import MAX_DISPLAY_VALUE, finite_integer, finite_number


class TestFiniteNumber:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, 0),
            (17, 17),
            (1.25, 1.25),
            (" 1.25 ", 1.25),
            ("1e3", 1000.0),
            (MAX_DISPLAY_VALUE, MAX_DISPLAY_VALUE),
        ],
    )
    def test_accepts_existing_numeric_forms(self, value, expected):
        assert finite_number(value) == expected

    @pytest.mark.parametrize("value", [None, True, False, "", "not-a-number"])
    def test_invalid_values_use_default(self, value):
        assert finite_number(value, default=3.5) == 3.5

    @pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "nan", "Infinity"])
    def test_nonfinite_values_use_default(self, value):
        assert finite_number(value, default=3.5) == 3.5

    @pytest.mark.parametrize("value", [MAX_DISPLAY_VALUE + 1, -(MAX_DISPLAY_VALUE + 1), "1e16"])
    def test_out_of_bound_values_use_default(self, value):
        assert finite_number(value, default=3.5) == 3.5

    def test_huge_integer_is_rejected_without_float_round_trip(self):
        huge = 10**400
        assert finite_number(huge, default=2.5) == 2.5

    def test_oversized_default_is_safely_normalized(self):
        assert finite_number("not-a-number", default=10**400) == 0


class TestFiniteInteger:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, 0),
            (17, 17),
            (1.9, 1),
            ("17", 17),
            (" 17 ", 17),
            (MAX_DISPLAY_VALUE, MAX_DISPLAY_VALUE),
        ],
    )
    def test_accepts_existing_count_forms(self, value, expected):
        assert finite_integer(value) == expected

    @pytest.mark.parametrize("value", [None, True, False, "", "1.0", "not-a-number"])
    def test_invalid_values_use_default(self, value):
        assert finite_integer(value, default=7) == 7

    @pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "nan", "Infinity"])
    def test_nonfinite_values_use_default(self, value):
        assert finite_integer(value, default=7) == 7

    @pytest.mark.parametrize(
        "value", [MAX_DISPLAY_VALUE + 1, -(MAX_DISPLAY_VALUE + 1), "10000000000000000"]
    )
    def test_out_of_bound_values_use_default(self, value):
        assert finite_integer(value, default=7) == 7

    def test_huge_integer_is_rejected_exactly(self):
        assert finite_integer(10**400, default=7) == 7
