# ADR 0066: Count confirmed Claude Code subagents

- Status: Accepted
- Date: 2026-11-13
- Extends: [ADR 0007](0007-incremental-transcript-with-versioned-totals.md)
- Supersedes: the release slots for schema 2 and the editor in [ADR 0060](0060-evolve-one-config-with-collection-independent-views.md)

## Context

The main status line reads the parent transcript. Claude Code writes subagent
messages to separate child transcripts. A Claude Code 2.1.319 parent transcript
with three confirmed background launches had zero sidechain records. Claude
documents the [separate transcript paths](https://code.claude.com/docs/en/hooks#subagentstop).
The main transcript's structured result format is observed local evidence.

## Decision

Count distinct agent IDs from structured completion and background launch
results matched to parent `Agent` or legacy `Task` tool-use IDs. Only use a
record-level result when it can be attributed to one tool result. Ignore
failed launch results and deduplicate repeated tool results and agent IDs.
Report confirmed agents with agent units. When there are no confirmations,
show zero only for readable parent activity without unresolved launch or
sidechain evidence. Indicate unavailability or show explicitly labelled legacy
sidechain message counts in the other cases.

Use the existing locked, transcript-scoped incremental cache. Cache schema 6
replays earlier entries to collect launch identities. Keep child transcript
reads, hook installation and per-agent display outside this fix. Keep the
existing `TOOLS.subagents` field ID and visibility controls.

## Consequences

Host versions that omit a usable agent ID may leave the count unavailable or
report only confirmed launches. A confirmed count is cumulative over the
available transcript and does not represent currently running subagents.
The correctness fix ships as 0.6.0, schema 2 moves to 0.6.1, and the editor
moves to 0.6.2. The roadmap owns the revised remaining release slots.
