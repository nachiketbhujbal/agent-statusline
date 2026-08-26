# ADR 0006: Route every subprocess through a cached probe

- Status: Accepted
- Date: 2026-08-23

## Context

The status line redraws every few seconds. Reading git state took four
subprocesses costing roughly 63ms on every redraw, which made the whole line
render in 110ms and flicker visibly.

## Decision

Anything with a process cost goes through `probe(key, ttl, fn)`, which persists
results and reuses them for a few seconds. `statusline.py` never calls a
subprocess directly. Git state is collected by a single
`git status --porcelain=v2 --branch` call rather than four.

## Consequences

A warm redraw costs around 30ms against a 15ms floor for bare Python startup,
and the flicker is gone. New probes must pick a TTL. If flicker returns, the
next levers are the `ps` sweep's TTL and then Python startup itself, which is
the hard floor.
