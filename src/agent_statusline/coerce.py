"""Safe numeric coercion at the untrusted host-input boundary.

The host payload and transcript are decoded by the standard-library JSON
decoder, which accepts non-finite numeric literals.  Keep that handling in one
small, host-agnostic module so renderers can degrade instead of raising while
retaining the distinction between fractional measurements and counts.
"""

import math
from typing import Any, Union

# Values beyond this boundary cannot produce useful status-line output.  It is
# comfortably above realistic token/byte/count values while bounding formatting
# work and avoiding a lossy conversion of arbitrary-size integers to float.
MAX_DISPLAY_VALUE = 10**15
Number = Union[int, float]


def _valid_default(default: Number) -> Number:
    """Return a safe numeric default supplied by a caller."""
    if isinstance(default, bool):
        return 0
    if isinstance(default, int):
        return default if abs(default) <= MAX_DISPLAY_VALUE else 0
    if isinstance(default, float) and math.isfinite(default) and abs(default) <= MAX_DISPLAY_VALUE:
        return default
    return 0


def finite_number(value: Any, default: Number = 0.0) -> Number:
    """Return a bounded finite number, preserving exact integer inputs.

    Numeric strings retain the existing ``float`` acceptance used by the
    renderer, including surrounding whitespace and exponent notation.  Bool,
    null, invalid, non-finite, and out-of-bound values return ``default``.
    """
    fallback = _valid_default(default)
    if value is None or isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value if abs(value) <= MAX_DISPLAY_VALUE else fallback
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return fallback
    if not math.isfinite(number) or abs(number) > MAX_DISPLAY_VALUE:
        return fallback
    return number


def finite_integer(value: Any, default: int = 0) -> int:
    """Return a bounded finite integer for count-like host values.

    Numeric strings retain the existing ``int`` acceptance.  Finite float
    inputs retain Python's existing truncation semantics; booleans, null,
    invalid, non-finite, and out-of-bound values return ``default``.
    """
    fallback = _valid_default(default)
    if not isinstance(fallback, int):
        fallback = int(fallback)
    if value is None or isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value if abs(value) <= MAX_DISPLAY_VALUE else fallback
    try:
        if isinstance(value, float):
            if not math.isfinite(value) or abs(value) > MAX_DISPLAY_VALUE:
                return fallback
            number = int(value)
        elif isinstance(value, str):
            number = int(value)
        else:
            return fallback
    except (TypeError, ValueError, OverflowError):
        return fallback
    return number if abs(number) <= MAX_DISPLAY_VALUE else fallback
