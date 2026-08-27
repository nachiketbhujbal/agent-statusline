# ADR 0027: Measure cells and sanitize terminal output

- Status: Accepted
- Date: 2026-08-27

## Context

ADR 0010 bounds rows by terminal width, but the original implementation counted
Unicode code points rather than display cells. Wide characters could overflow
and combining marks could be over-counted. Host payloads and transcript labels
also reached stdout without removing newlines, bidirectional controls, or
terminal escape commands.

## Decision

Measure printable text with the standard library's Unicode combining and East
Asian Width properties. Combining marks occupy zero cells; wide and full-width
characters occupy two; other printable characters occupy one.

Sanitize every row label, separator, and segment before fitting. Preserve only
the project's intentional ANSI SGR colour sequences. Remove other escape
sequences and Unicode control/format characters, including physical line breaks
and bidirectional overrides. Clip only at complete code-point boundaries and
reserve display cells for ellipsis markers.

## Consequences

- Physical rows remain within their detected terminal-cell budget for narrow,
  wide, and combining Unicode.
- Untrusted host strings cannot inject rows, cursor movement, screen clearing,
  or bidirectional display controls.
- Approved colours and the ten-row field order remain unchanged.
- This is dependency-free and intentionally conservative; full grapheme-cluster
  shaping is outside the standard library and is not required for safe bounds.

## Evidence

Focused tests cover SGR preservation, control removal, wide and combining
measurement, wide-character clipping, injected line and terminal commands, and
the end-to-end terminal-cell width invariant.
