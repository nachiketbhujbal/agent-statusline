# ADR 0025: Bound ephemeral observation state

- Status: Accepted
- Date: 2026-08-26

## Context

The renderer retains incremental transcript offsets and changing rate-limit
observations so frequent redraws remain fast and provider behavior can be
measured. Neither file is an authoritative user record, but both grew for the
lifetime of the installation. Session- and path-qualified caches make a
lifecycle policy necessary.

The cost ledger is intentionally outside this decision. Its accounting records
have their own 35-day evidence policy under ADR 0022.

## Decision

Retain transcript-cache rows for at most 35 days after access and keep at most
512 recent transcripts. Touch the active row no more than hourly, avoiding a
state write on every redraw. Preserve the active row while pruning.

Cap the rate-limit observation log at one MiB. Normal redraws continue reading
only the last four KiB to detect an unchanged observation. Only a boundary
compaction scans and atomically republishes the log, retaining the newest whole
JSON records that fit. Malformed observation rows may be discarded because the
log is diagnostic evidence, not an accounting source.

## Consequences

- Transcript and rate-limit observation state cannot grow without bound.
- Recently active sessions keep incremental offsets and do not require a full
  transcript rescan.
- A session reopened after cache expiry is safely reparsed from byte zero.
- Rate-limit research retains recent evidence rather than an unlimited archive.
- Hot-path JSONL reads remain constant-sized between rare compactions.

## Evidence

Tests prove retention of the active transcript, removal of stale rows, the
512-row boundary, the byte boundary, malformed-row cleanup, private file mode,
and that an unchanged below-bound log never invokes the full-file reader.
