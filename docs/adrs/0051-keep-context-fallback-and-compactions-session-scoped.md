# ADR 0051: Keep context fallback and compactions session scoped

- Status: Accepted
- Date: 2026-10-23
- Supersedes: the last-payload fallback decision in [ADR 0049](0049-configure-context-warnings-at-stop-time.md); other settings and event behavior remain accepted.

## Context

Multiple Claude terminals redraw into shared local state. Transcript totals
are already keyed by transcript path, process observations by session identity,
and public metrics by session ID. However, when metrics are missing or unusable,
the context guard combined current-transcript tokens with the globally latest
payload's window size, regardless of session, and invented a one-million-token
window when that evidence was unavailable.

A bounded structural inspection found explicit compaction boundaries followed
by parent-linked summary records. The old parser recognized summary flags but
missed the system boundary subtype. Simply adding boundaries would double count
paired events. Equal counts across chats alone do not prove state crossover.

## Decision

Keep session metrics as the preferred context evidence. Bind last-payload
fallback to the hook's non-empty session ID and, when supplied, transcript path.
If the hook lacks a session ID, require a non-empty matching transcript path.
Do not warn when no positive, valid window size can be established. Preserve
warning configuration, Stop timing, and the public metrics schema.

Count explicit `system` / `compact_boundary` records immediately, preserve the
legacy direct `compact` and `compact_boundary` types, and pair each boundary
with its following boolean summary marker. A matching parent identifier avoids
counting twice; identifier-free legacy records use the pending boundary. A
summary with an explicitly different parent is a separate event. Summary-only
records continue to count. Broad type substrings and truthy non-boolean flags
are not evidence of compaction.

Persist pending pairing state per transcript in cache schema 4. Rebuild older
caches from their transcripts. Preserve locked atomic publication, retention,
and the approved display. Verify interleaved fallback, incremental pairs, old
caches, and six simultaneous synthetic renderer/hook sessions.

## Consequences

A hook may remain quiet until current-session window evidence is available;
this is preferable to advising compaction using another chat's denominator.
The shared last-payload file remains diagnostic state. Transcript counts include
inherited history on resume or fork and are logically separate per path, not a
security boundary between processes under the same user account.

No ledger migration, installer change, runtime dependency, networking, live
settings mutation, or general configuration file belongs to this patch.
