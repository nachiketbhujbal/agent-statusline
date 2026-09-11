# ADR 0027: Measure cells and sanitize terminal output

- Status: Accepted
- Date: 2026-09-11

## Context

ADR 0010 bounds rows by terminal width, but the original implementation counted
Unicode code points rather than display cells. Wide characters could overflow
and combining marks could be over-counted. Host payloads and transcript labels
also reached stdout without removing newlines, bidirectional controls, or
terminal escape commands.

Nested Git discovery also reused the discovered child repository as the working
directory for later probes, so the `SYSTEM` row could report disk space for a
different path than the current workspace. Finally, rounding fractional 5h/7d
allowance percentages could display 100% before actual exhaustion.

## Decision

Measure printable text with the standard library's Unicode combining and East
Asian Width properties. Combining marks occupy zero cells; wide and full-width
characters occupy two; other printable characters occupy one.

Sanitize every row label, separator, and segment before fitting. Preserve only
the exact ANSI SGR sequences owned by the package. Remove every other escape
sequence and Unicode control, format, or surrogate character, including
physical line breaks and bidirectional controls. Clip only at complete code-
point boundaries and reserve display cells for ellipsis markers.

Continuation lines start with the package's dim SGR before their indentation.
This preserves indentation under Claude Code's observed leading-whitespace
trimming behavior; it is measured host behavior to re-verify if the host
changes, not a permanent host guarantee.

Use a separate nested-Git lookup path for branch display without rebinding the
current-workspace path used by the disk probe. Display 5h/7d allowance usage as
a floored integer so a fractional value below 100 cannot claim exhaustion;
retain the burn-rate decimal and use the original numeric value for overage.

## Consequences

- Physical rows remain within their detected terminal-cell budget for narrow,
  wide, and combining Unicode.
- Untrusted host strings cannot inject rows, cursor movement, screen clearing,
  arbitrary styling, or bidirectional display controls.
- Approved colours, ten-row order, and segment priorities remain unchanged.
- Nested Git display and `SYSTEM` disk evidence remain independently bound.
- This stays dependency-free. Full grapheme-cluster shaping is outside the
  standard library and is not required for conservative width bounds.

## Evidence

Focused and end-to-end tests cover exact package-SGR preservation, unknown SGR
and control removal, wide and combining measurement, whole-code-point clipping,
physical-width bounds, two-line continuation alignment, nested-Git disk keys,
floored fractional allowance values, the 100% boundary, and overage display.
