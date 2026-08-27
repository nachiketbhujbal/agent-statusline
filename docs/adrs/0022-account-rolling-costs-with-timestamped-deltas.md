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

Preserve all three fields and add a versioned stream of positive cost deltas to
`cost-ledger.json`. Each delta records its observation time and session. Rolling
totals sum only deltas inside the requested horizon.

The tracking start is explicit. Until a complete horizon has elapsed after the
upgrade, render its amount with `≥`: the amount is a proven lower bound because
pre-upgrade timing is unknowable. The marker disappears independently after 24
hours, 7 days, and 30 days. Lifetime session, `last5`, and `all` totals retain
the existing compatible ledger data.

Retain only the event history required by the longest window. Unknown or
malformed event schemas never receive a complete-window claim.

## Consequences

No cost field is removed. Values converge automatically from honest lower
bounds to complete rolling totals without fabricating a migration history.
Overlapping redraws cannot double-record a delta because event publication and
session cost updates share the ledger transaction introduced by ADR 0021.
