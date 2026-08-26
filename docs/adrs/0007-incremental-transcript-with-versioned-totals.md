# ADR 0007: Parse the transcript incrementally and version the totals

- Status: Accepted
- Date: 2026-08-24

## Context

Cumulative session facts live in a session transcript that grows to megabytes.
Re-reading it on every redraw is not viable, and caching accumulated totals
across redraws makes the cache's shape part of the on-disk contract.

## Decision

Store a byte offset plus accumulated totals per transcript and read only the
bytes appended since the last redraw, holding back a partial trailing line.
`SCHEMA` versions the shape of those totals and must be bumped whenever an
accumulated field is added or changed.

## Consequences

Redraw cost is independent of transcript size. Forgetting the `SCHEMA` bump is
the specific failure this guards against: existing caches keep their old shape
and the new field stays empty forever, with no error anywhere.
