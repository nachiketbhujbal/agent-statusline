# ADR 0010: Fit rows by wrapping to two lines before truncating

- Status: Accepted
- Date: 2026-08-26

## Context

Rows overflowed narrow terminals and wrapped wherever the terminal chose. Two
clean alternatives existed: drop overflowing segments and never wrap, or wrap
freely and never drop. Claude Code caps how many lines the status line may
occupy and drops whole rows from the bottom when it runs out, visibly so as the
input box grows.

## Decision

Fit each row in three stages: clip any single segment wider than the budget,
pack segments onto at most two lines, then drop what remains and mark it with an
ellipsis. A row that fits on one line is never wrapped.

## Consequences

Overflow costs the least important segment of a row rather than the last rows
entirely. Ten rows cannot silently become twenty. `MAXLINES` is the knob, and
raising it trades segment loss for row loss. Width is read on every render, not
cached at import, so live terminal resizes are picked up.
