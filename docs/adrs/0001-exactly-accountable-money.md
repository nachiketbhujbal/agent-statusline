# ADR 0001: Show only money that can be accounted exactly

- Status: Accepted
- Date: 2026-08-24

## Context

A status line that is confidently wrong about money is worse than one that says
nothing. Two tempting figures are not exact: a cost derived from token counts
times a local price table drifts silently the moment prices change, and a
"spend since overage began" figure can only start counting when the status line
first noticed the crossing, not when it happened.

## Decision

Session cost is the payload's `total_cost_usd` passed straight through, never
recomputed. A derived figure earns a currency symbol only if it can be
accounted exactly; otherwise it is not shown.

## Consequences

The earlier "credits drawing $X since HH:MM" field was removed: it
under-reported by however long the gap was between overage starting and the
status line first rendering, observed at roughly twelve minutes. The credit balance is not
displayed at all, because it is not obtainable locally. Unit-free ratios such as
`0.12x vs all-uncached` remain acceptable, as they are billing multipliers
rather than prices and never render a currency symbol.
