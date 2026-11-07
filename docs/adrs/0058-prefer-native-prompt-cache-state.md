# ADR 0058: Prefer native prompt-cache state

- Status: Accepted
- Date: 2026-11-07
- Supersedes: [ADR 0008](0008-observe-the-cache-ttl.md)
- Extends: [ADR 0047](0047-normalize-claude-acquisition-facts.md)

## Context

Claude Code v2.1.251 added a documented `prompt_cache` payload. The prior
newest-write inference ignores that signal and collapses mixed TTL history.
Five-minute TTL is valid for several request and billing modes. A local
expiry estimate cannot guarantee that the next request misses every prefix.
See the sourced [research](../RESEARCH.md#claude-code-status-line-capability-audit).

## Decision

Normalize only native lifetime facts needed by the existing `CACHE.ttl`
field into an internal `cache` group. Require boolean warmth and observation
flags and a supported TTL; ignore a malformed optional expiry clock. Prefer
this group from the current payload over transcript history. Do not persist
or borrow cache state from another session. Native expiry may transition a
previously warm payload to cold on a later redraw. An unobserved cache remains
unobserved, not an inferred miss.

When native state is absent or malformed, retain the legacy newest-write
bucket and one-hour initial fallback, explicitly labelled estimated or
assumed. Say `possibly cold` when its window elapses. Use neutral TTL styling;
reserve the cold warning for state rather than the five-minute duration.

## Consequences

Retain row order, field IDs, selection, width fitting and plain output.
Native cache state renders without a transcript. Existing transcript hit
rate, write totals and relative multiplier retain their scope and calculation.
No ledger, installer, configuration schema or public metrics schema changes.
No runtime dependency, network access, new probe or timer process is added.
ADR 0013's decision to omit the animated bar remains accepted. Additional
host metrics follow in independent opt-in releases.
