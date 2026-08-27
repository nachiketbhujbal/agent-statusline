# ADR 0024: Scope process probes by session

- Status: Accepted
- Date: 2026-08-26

## Context

The process probe reports both machine-wide Claude totals and the PID, process
count, and resident memory for the session that invoked the renderer. The probe
cache is shared by every concurrent session. Caching that mixed result under
the single key `procs` allowed the first session rendering inside an eight-
second window to lend its session-specific values to every other session.

Qualifying the key creates one cache entry per active session. Without a
lifecycle bound, old session, repository, and working-directory keys would
remain forever.

## Decision

Cache process results under the opaque Claude session identifier. When the host
does not supply one, use the renderer's parent process as a local fallback.
Keep the existing combined process sweep: recomputing the machine-wide values
once per active session is preferable to displaying a false per-session value,
and avoids a second subprocess or a more complex split cache.

Prune all probe-cache rows older than seven days and retain no more than 256
recent rows. Malformed rows are stale evidence and are replaced. The cache is
an optimization only; pruning never removes an authoritative product record.

## Consequences

- Concurrent sessions no longer share `this session` PID or RSS values.
- A system with several active sessions may perform one `ps` sweep per session
  per eight-second TTL rather than one sweep globally.
- Per-session keys and other path-qualified probes remain bounded.
- The process result remains one internally consistent snapshot.

## Evidence

Focused tests prove that distinct session payloads request distinct keys, that
the two scopes preserve independent cached results, and that stale, excessive,
and malformed rows are pruned or replaced.
