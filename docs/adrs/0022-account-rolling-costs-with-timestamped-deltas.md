# ADR 0022: Account rolling costs with timestamped deltas

- Status: Accepted
- Date: 2026-09-11

## Context

The `24h`, `7d`, and `30d` fields are useful and remain part of the approved
display. The original ledger assigned a session's complete lifetime cost to
every window containing its latest update. Resuming an old session could
therefore make historical cost appear recent.

Existing ledger snapshots cannot reveal when their historical cost accrued.
Inventing that timing or deriving it from tokens would violate
[ADR 0001](0001-exactly-accountable-money.md).

## Decision

Preserve all three fields and store a versioned stream of positive lifetime-
cost deltas inside `cost-ledger.json`. Each ordinary event records observation
time, the newest known assistant timestamp, session, delta, and resulting
lifetime. Assistant time is preferred for attribution; missing or malformed
evidence falls back to observation time, and future evidence is clamped to it.

First sightings and migrated lifetime totals are non-accrual seeds. A seed is
counted when its session provably began inside a window, excluded when lifecycle
evidence proves it ended before the window, and otherwise reported as
unattributed. A window with unattributed or invalid evidence renders `≥` before
its exact known amount. Each horizon makes that completeness decision
independently, so a 24-hour figure may be a lower bound while 7-day and 30-day
figures are complete.

Session mutation, seed migration, event append, and rolling calculation share
the locked ledger transaction introduced by ADR 0021. Repeated sightings do not
duplicate seeds, and only finite positive lifetime increases append ordinary
events. Event timestamps and amounts must be finite and internally consistent;
invalid schemas or events contribute no amount and prevent a complete claim.
Retain at least 35 days of valid events, and never prune malformed evidence merely
to manufacture completeness.

Journal-shaped fields without a recognized schema are preserved unchanged and
treated as incomplete evidence. If ledger storage fails before the updater can
read history, the current payload remains renderable only as a lower bound; a
failure after a complete aggregate was computed retains that aggregate.

Lifetime session cost, resume/base/run behavior, `last5`, `all`, row order, and
every non-cost field remain unchanged.

## Consequences

No cost field is removed or estimated. Rolling values begin as exact lower
bounds where historical timing is unknowable and become complete automatically
as evidence permits. Several turns observed in one redraw remain one delta at
the newest assistant timestamp because transcripts expose tokens, not exact
per-turn cost; the implementation never prorates or introduces a price table.
