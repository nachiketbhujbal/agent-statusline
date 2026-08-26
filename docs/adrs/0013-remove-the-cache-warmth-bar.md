# ADR 0013: Remove the cache warmth bar

- Status: Accepted
- Date: 2026-08-26

## Context

The cache row carried a draining bar and a countdown. The prompt cache TTL
slides — every request that hits the cache refreshes it — and the status line
redraws turn by turn, so the bar sat pinned near full and the countdown read
close to its maximum on nearly every render. It was measuring time since the
last turn, which the user already knows.

## Decision

Delete the bar and the countdown. Show the live TTL window and a wall-clock
expiry time instead, alongside the hit rate, the effective multiplier, and the
per-bucket write split.

## Consequences

The cache row now changes only when something changed. A watcher process was
considered and rejected: it would run continuously to animate a number whose
only interesting state is "you have been idle", which the expiry clock already
reports. Removing a field that proved useless is the expected outcome of showing
anything cheaply derivable until it earns its place.
