# ADR 0031: Adopt a practical local-tool threat model

- Status: Accepted
- Date: 2026-08-29

## Context

The installation-ownership hardening in ADR 0020 grew across several review
rounds by closing one same-user filesystem race after another: a checked
directory replaced by a symlink, then a checked root replaced by an ordinary
directory, then a checked entry's own subdirectory. Each closure is real
correctness work, but the pattern has no natural ceiling -- every race closed
at one level of indirection exposes an equivalent one at the next, and each
closure adds machinery (descriptor binding, restoration bookkeeping) that a
local, unprivileged, single-user tool does not otherwise need. Continuing
indefinitely would eventually make the installer defend against an active
adversary sharing the user's own account, which is a different product than a
personal status-line installer.

## Decision

`agent-statusline` is a local, unprivileged tool. It runs as the current user,
reads host-provided payloads and transcripts, keeps private local state, and
mutates that user's own Claude configuration only during an explicit install
or uninstall command. It does not claim to defend that user from another
process already running with the same user's filesystem authority: such a
process can edit the same configuration directly, with or without racing this
installer, so racing the installer buys an attacker nothing a direct edit does
not already give them.

**In scope:**

- Malformed, unreadable, non-object, or otherwise unsupported configuration.
- Symlinks and other non-regular entries encountered during normal operation,
  including ones that resolve outside the selected configuration directory.
- Accidental ownership collisions with another status line, hook, interpreter,
  or checkout path.
- Ordinary filesystem errors: missing directories, permission failures, full
  storage, interrupted publication, and failed backup or cleanup.
- Atomic single-file publication with private permissions, useful backups,
  explicit recovery reporting, and preservation of unrelated configuration.

**Explicitly out of scope:**

- A malicious process with the same user ID deliberately renaming directory
  objects or swapping links inside a narrow check-then-use window of this
  installer's own operations.
- A compromised kernel, filesystem implementation, Python runtime, package
  installation, or administrator/root account.
- Guaranteeing an atomic commit across the checkout symlink and the settings
  file: they are two independent filesystem objects with no shared commit
  point.
- Guaranteeing successful rollback when both the primary operation and the
  rollback operation experience separate failures.

Out of scope does not mean silent failure. When recovery cannot complete, the
installer reports that fact, names the affected package-owned state, and
leaves a clear manual next step -- best-effort recovery with explicit failure
reporting, never a claim that no inconsistent state can result.

Existing hardening -- descriptor-relative publication, fail-closed parsing,
atomic replacement, ownership anchored to an exact written command, and
backup before mutation -- is retained as compact, dependency-free, tested
defense in depth, even where it exceeds this boundary. It is a ceiling on this
class of work, not a precedent: a future same-user pathname race found one
level deeper than an already-closed one is evaluated against this boundary
before being treated as a release-blocking defect, and is not, by itself,
grounds to add further machinery whose sole purpose is closing it.

## Consequences

Documentation describing install/uninstall recovery states the relationship
between the checkout symlink and the settings file truthfully: best-effort,
not atomic, with the outcome reported when restoration itself fails, rather
than promising a stronger guarantee than the implementation gives. A same-user
pathname race identified during future work is a private security finding
evaluated against this boundary, not an automatic tracked defect; exact
evidence and reproduction stay in the project's private review channel, and
tracked records describe the boundary this ADR sets rather than the
reproduction itself.
