# ADR 0014: Never exercise cost paths against the live ledger

- Status: Accepted
- Date: 2026-08-24

## Context

Rendering the status line by hand mutates the ledger. This corrupted real spend
figures twice in one day: once from a test that bumped the payload cost and
restored it, and once from simply re-rendering a saved payload after the live
session had moved on. Both looked like a cost decrease, both banked a phantom
run, and the session's reported cost roughly doubled.

## Decision

Previews and tests point `AGENT_STATUSLINE_STATE` at a throwaway directory. Run
detection keys on the process id, so a same-pid decrease is treated as a stale
payload and the high-water cost is kept; the no-pid fallback also keeps the
higher figure.

## Consequences

The test suite redirects the state directory before any package import, because
the path is resolved at import time, and no test may touch the real config
directory. A corrupted row is repaired by resetting `cost_base` to zero and
`cost_run` and `cost` to the true value.
