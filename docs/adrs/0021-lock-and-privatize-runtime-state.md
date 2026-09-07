# ADR 0021: Lock, atomically publish, and privatize runtime state

- Status: Accepted
- Date: 2026-08-26

## Context

The status line and its hooks are separate short-lived processes that can read
and update the same package-owned ledger, transcript cache, probe cache,
payload, and rate-limit history. Plain read-modify-write sequences can overlap
and lose a completed update. Predictable temporary names and permissive default
modes can also expose paths, usage, and cost data or let an interrupted write
replace valid state with partial content.

The storage boundary must remain dependency-free and preserve the practical
local-tool threat model in [ADR 0031](0031-practical-local-threat-model.md). It
must handle ordinary malformed state, unsupported filesystem entries,
concurrent package processes, and expected I/O failures. It does not need to
defend against a hostile process already running with the same user's
filesystem authority.

## Decision

All package-owned runtime persistence uses one standard-library storage service.
Each state file has a private sidecar lock, and each JSON read-modify-write holds
an exclusive POSIX advisory lock across the read, update, and publication.
Read-only JSON access may use a shared lock. JSONL tail comparison and append
remain under one exclusive lock.

JSON and text publication uses a unique temporary file in the destination
directory, mode `0600`, followed by flush, file sync, and atomic replacement of
that one destination. Directory sync is best effort. Lock files are also
`0600`; a state root created by the package is `0700`. An existing state root's
mode is not changed.

Package state paths are lazy: the state root is created, resolved, and verified
only when a filesystem operation first uses an entry, not while modules import.
A package state name must identify one direct, non-empty filename inside that
root. Before the service reads, permissions, locks, appends to, or replaces a
state or lock entry, it rejects a final symlink or other non-regular entry.
Opens use `O_NOFOLLOW` where the platform provides it and verify the opened
descriptor is regular. Malformed JSON, decoder resource errors, and unsupported
top-level or nested package-cache shapes degrade to fresh or normalized state
without discarding valid sibling records.

This decision provides atomicity per state file, not across multiple files. It
supports macOS and Linux, where the required POSIX locking primitives exist;
Windows support is out of scope. It also does not claim protection from a
deliberate same-user pathname swap in a narrow check-then-use window, a
compromised runtime or kernel, or an administrator account.

## Consequences

Concurrent package processes serialize their short state transactions, so
distinct valid updates are preserved and readers do not observe partially
serialized JSON. Expected publication failures leave the prior destination
bytes intact, release the lock, close descriptors, and remove only the unique
temporary entry created for that attempt.

Every package-owned producer must use the shared service rather than opening,
permissioning, replacing, or appending runtime state independently. The added
locking and sync work is intentionally local and bounded; no runtime dependency,
transaction journal, multi-file commit protocol, or stronger hostile-process
security claim is introduced.

Runtime persistence remains optional display metadata. A consumer may contain
an expected storage failure with its established stateless fallback or a result
already computed inside a transaction, but the storage operation itself still
fails closed: it does not follow an unsafe entry, publish to an unverified root,
or report an uncommitted write as successful.
