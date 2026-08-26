# ADR 0009: Suppress derived rate-limit figures above 100%

- Status: Accepted
- Date: 2026-08-24

## Context

Burn rate and end-of-window projection are both computed from
`used_percentage`. Whether that number keeps climbing past 100% or pins near it
during credit-funded overage is unresolved: it was observed to climb 70 → 102
and then sit at exactly 102% across roughly forty minutes of heavy work, and
"pinned" is indistinguishable from "stale" in a single reading.

## Decision

Above 100%, hide the burn rate and the projection and show `+N% over` instead,
taken straight from the payload with no inference. Log every change in either
window to `rate-limit-history.jsonl` so the question can be settled from data.

## Consequences

A frozen reading cannot produce a falling burn rate and a shrinking projection
while real spend continues. The log costs a few bytes per change and nothing on
an unchanged render. If the figure is shown to climb, this ADR should be
superseded rather than edited.
