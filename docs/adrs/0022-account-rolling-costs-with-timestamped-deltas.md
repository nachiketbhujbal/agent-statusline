# ADR 0022: Account rolling costs with timestamped deltas

- Status: Accepted
- Date: 2026-08-26

## Context

The status line's `24h`, `7d`, and `30d` fields are useful and remain part of
the approved display. The original ledger, however, stored only each session's
lifetime total and last-update time. It calculated a rolling window by assigning
the complete lifetime cost to the session's most recent update. Resuming an old
session could therefore make historical cost appear recent.

Existing ledger snapshots cannot reveal when their historical cost accrued.
Inventing that timing would violate [ADR 0001](0001-exactly-accountable-money.md).

## Decision

Preserve all three fields and add a versioned stream of positive lifetime-cost
deltas to `cost-ledger.json`. Each delta records its observation time, newest
known assistant timestamp, and session. Rolling totals attribute ordinary
deltas by the assistant timestamp, falling back to observation time.

First sightings are non-accrual seed records. During migration, a seed is fully
counted when its session began inside the window, excluded when it ended before
the window, and otherwise reported as unattributable. Render `≥` only for the
last case or invalid evidence: the amount remains a proven lower bound because
pre-upgrade timing is unknowable. A window can therefore be complete before the
journal itself reaches that age when every seed is already classifiable.
Lifetime session, `last5`, and `all` totals retain the existing compatible
ledger data.

Retain 35 days of events, giving the longest 30-day window margin around
observation and pruning boundaries. Unknown or malformed event schemas never
receive a complete-window claim.

## Consequences

No cost field is removed. Values converge automatically from honest lower
bounds to complete rolling totals without fabricating a migration history.
Overlapping redraws cannot double-record a delta because event publication and
session cost updates share the ledger transaction introduced by ADR 0021.
