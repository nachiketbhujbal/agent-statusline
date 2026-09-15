# ADR 0047: Normalize Claude acquisition facts before rendering

- Status: Accepted
- Date: 2026-09-15

## Context

ADR 0046 separated host acquisition from presentation, but the renderer still
read Claude Code's payload and transcript structures directly. That left no
single internal boundary for another local consumer or a future host adapter.

## Decision

Add a dependency-free Claude acquisition adapter that emits grouped normalized
facts for identity, workspace, model, context, tokens, limits, activity, and
exact money. Optional evidence stays absent when Claude does not supply it.
Exact cost continues to come only from Claude's cumulative cost field and is
never inferred from tokens.

The existing renderer consumes that adapter while preserving its ten rows,
field order, values, installer behavior, ledger semantics, and state files.
The normalized shape is internal in this release; a separately versioned public
session-metrics contract may build on it later without exposing Claude's raw
payload or transcript cache.

## Consequences

Host interpretation now has one explicit seam. The adapter adds no runtime
dependency, networking, hook, configuration, or public file. Codex parsing and
public session metrics remain later patches with their own evidence.

ADR 0046's acquisition, presentation, privacy, and exact-money decisions remain
accepted. This ADR supersedes only its suggested follow-on patch order: the
maintainer prioritized the local integration needs in issues 30 through 32, so
v0.4.2 defines public per-session metrics and v0.4.3 addresses configurable
context warnings and Stop timing. The synthetic-fixture Codex rollout parser
and any opt-in Codex collector/query surface follow those releases.
