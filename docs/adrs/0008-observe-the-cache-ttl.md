# ADR 0008: Observe the cache TTL rather than assuming it

- Status: Accepted
- Date: 2026-08-24

## Context

The payload carries no cache TTL, expiry, or warmth field. A hardcoded one-hour
assumption was wrong in a case that matters: when an account crosses its
five-hour limit into credit-funded overage, the prompt cache drops from one hour
to five minutes, mid-session, between one turn and the next.

## Decision

Read the TTL from which `cache_creation` bucket the *newest* write landed in,
`ephemeral_1h_input_tokens` or `ephemeral_5m_input_tokens`. `CACHE_TTL_S` is
only a fallback for before the first write is seen. Render the `5m` window in
red, because it is the state worth reacting to.

## Consequences

Cumulative bucket totals must never be used for this: they lag, and a cumulative
comparison once reported a warm hour while every recent write was going to the
five-minute bucket — promising 59 warm minutes when the real answer was four.
