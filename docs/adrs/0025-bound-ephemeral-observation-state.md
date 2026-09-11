# ADR 0025: Bound ephemeral observation state

- Status: Accepted
- Date: 2026-09-11

## Context

The renderer retains short-lived probe results, incremental transcript offsets,
and changing rate-limit observations so frequent redraws remain fast. None is an
authoritative user record, but path- and session-qualified keys allowed all
three stores to grow for the lifetime of the installation.

The cost ledger is intentionally outside this decision. Its accounting records
have their own evidence and retention policy under ADR 0022.

## Decision

Expire probe-cache rows more than seven days after observation and retain at
most 256 rows. Preserve the active probe row while removing the oldest remaining
valid observations. Malformed, non-finite, and future-dated rows are not valid
retention evidence.

Expire transcript-cache rows more than 35 days after access and retain at most
512 rows. Preserve the active transcript and its coupled incremental offset and
totals. Touch the active row no more than hourly. Stamp legacy rows that lack a
valid access time once during migration so they can later expire without being
discarded immediately.

Compact the diagnostic rate-limit observation log at one MiB under its existing
exclusive lock. Normal unchanged redraws continue reading only the last four
KiB. Boundary compaction scans through validated descriptors and atomically
publishes the newest contiguous whole-record suffix that fits, discarding
malformed rows. Always preserve the newest valid observation; a single
pathologically oversized record may therefore exceed the generic helper's
requested bound, though real rate-limit records are far smaller than one MiB.

## Consequences

- Ephemeral observation state no longer grows without a lifecycle bound.
- Active sessions keep cached probes and transcript offsets instead of paying a
  cold recomputation or complete transcript replay.
- A transcript reopened after expiry is safely parsed from byte zero.
- Rate-limit research retains recent evidence rather than an unlimited archive.
- Hot-path JSONL reads remain constant-sized between rare compactions.
- Existing private modes, locks, final-entry refusal, atomic publication, and
  failure cleanup remain in force.

## Evidence

Regressions prove exact age and count boundaries, active-row survival, legacy
timestamp migration, hourly transcript touching, monotonic transcript totals
and offsets, newest-rate-record survival, byte-bound malformed-row compaction,
prior-byte preservation on publication failure, and a tail-only unchanged hot
path.
