# ADR 0048: Publish versioned local session metrics

- Status: Accepted
- Date: 2026-09-15

## Context

The status-line render payload and incremental transcript contain useful local
session facts, but other hooks and tools do not receive that same evidence.
Existing state files are internal caches: consumers cannot safely infer their
shape, and the single last-payload file can belong to another concurrent
session.

## Decision

On every eligible render, publish one schema-versioned snapshot for the current
non-empty host session identifier. The filename contains a bounded SHA-256 of
the opaque identifier rather than the identifier itself; the JSON object retains
the identifier so its identity is explicit. Publish through the existing
private, locked, atomic storage service.

Expose the supported object through `agent-statusline metrics <session-id>` so
ordinary consumers do not need to construct filenames. Schema version 1 covers
producer, host, session, model, context, exact lifetime session cost, turns,
line counts, title, and lifecycle timestamps. Optional fields are absent when
unknown. Additive fields may enter version 1; removals or meaning changes require
a new schema and filename prefix.

`cost_usd` is present only when Claude supplies an exact current-run value and
the ledger can account for the session lifetime exactly. It is never inferred
from tokens or a price table.

Retain snapshots for 35 days and at most 512 sessions, with maintenance claimed
at most hourly. A selected old or excess snapshot is re-read and compared under
its own lock before deletion so a concurrent refresh wins. Set
`AGENT_STATUSLINE_SESSION_METRICS=0` to disable new writes. The installed
self-test exercises the schema from synthetic state.

## Consequences

Local integrations gain a stable, concurrency-safe contract without reading
internal transcript or ledger caches. The Claude display, row order, installer,
hooks, and exact-money rules do not change. Snapshot contents remain sensitive
local state and are not telemetry or publication-safe evidence.
