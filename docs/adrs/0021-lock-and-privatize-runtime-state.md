# ADR 0021: Lock, atomically publish, and privatize runtime state

- Status: Accepted
- Date: 2026-08-26

## Context

Claude Code may start overlapping status-line and hook processes. The original
implementation used one predictable `.tmp` name per state file and performed
separate unlocked reads and writes. Overlap could lose a ledger update, regress
a transcript offset, drop a probe-cache entry, or make one process fail to
rename a temporary file another process already consumed. State files also
used the caller's umask even though they contain local paths, usage, and cost
history.

## Decision

All mutable JSON and JSONL state is coordinated with a private sidecar lock and
POSIX advisory locking. Read-modify-write operations hold one exclusive lock.
Published files use a unique same-directory temporary file, mode `0600`, file
flush, atomic replacement, and a best-effort directory flush. Append-only state
is written and flushed while holding the same lock.

The state directory is created with mode `0700` when absent. Existing Claude
configuration-directory permissions are not changed. Runtime support remains
macOS and Linux; native Windows is outside the package contract.

## Consequences

Concurrent redraws serialize only short state transactions and cannot consume
one another's temporary files. State stays local and private by default. Every
state producer must use the shared storage service; direct ad hoc JSON writes
are prohibited and concurrency behavior is covered by subprocess tests.
