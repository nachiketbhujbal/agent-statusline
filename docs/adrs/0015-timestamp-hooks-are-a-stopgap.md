# ADR 0015: Treat the message-timestamp hooks as a removable stopgap

- Status: Accepted
- Date: 2026-08-23

## Context

Claude Code has a native `showMessageTimestamps` setting, but renders it only
when a server-side feature flag is also enabled. The flag is off for this
account, which is a staged rollout rather than a misconfiguration: nothing local
can change it, and editing the cached value is pointless because it is refetched.

## Decision

Two hooks stamp prompt-submit and turn-completion times as a temporary
substitute, and both files say so. `showMessageTimestamps` stays enabled so the
native feature switches itself on. `install.py` checks the flag and skips
installing the hooks where the native feature is already live.

## Consequences

These are the only components with a planned removal date. When the flag flips,
delete both hooks and their settings entries; leaving them installed would
duplicate every timestamp.
