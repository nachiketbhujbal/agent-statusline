# ADR 0024: Scope process probes by session

- Status: Accepted
- Date: 2026-09-11

## Context

The process probe reports both machine-wide Claude totals and the PID, process
count, and resident memory for the session that invoked the renderer. The probe
cache is shared by concurrent sessions. Caching that mixed result under one
`procs` key allowed the first session rendering within the eight-second TTL to
lend its session-specific values to every other session.

## Decision

Cache the combined process result under the host's opaque string `session_id`.
When the identifier is absent or not a string, use the renderer's parent PID as
a stable local fallback. Session and parent identities use separate key
namespaces so a host identifier cannot collide with a fallback key.

Keep one combined process sweep. Recomputing machine-wide totals once per active
session is preferable to displaying false per-session evidence, and it keeps
all values in one internally consistent snapshot without another subprocess.
Retention and entry-count limits remain the separate v0.2.7 boundary.

## Consequences

- Concurrent sessions do not share `this session` PID, process-count, or RSS
  evidence.
- The same session continues to reuse its result for the existing eight-second
  TTL.
- A machine with several active sessions may perform one process sweep per
  session per TTL instead of one sweep globally.
- This release does not prune old process-cache entries.

## Evidence

Focused regressions require distinct session keys, a stable non-colliding
parent fallback, opaque empty-string handling, and a single process snapshot for
both per-session and machine-wide values.
