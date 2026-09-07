# Roadmap

Release-scoped work belongs here. Ideas without a committed release stay in
[DEFERRED.md](DEFERRED.md).

## Release sequence

The hardening work is shipped as sequential, single-purpose 0.2.x patches rather
than one large release ([ADR 0030](adrs/0030-ship-hardening-as-small-pre-one-patches.md)).
Each release is cut from the preceding released state, carries only its own
implementation, tests, ADR and documentation, and is proven by its own gate and
installed-artifact evidence.

| Release | Primary purpose | Status |
| --- | --- | --- |
| 0.2.1 | Ownership-safe installation and removal | **Released** |
| 0.2.2 | Locked local quality gate | **Released** |
| 0.2.3 | Malformed host-input resilience | **Released** |
| 0.2.4 | Private, serialized runtime state | **Active** |
| 0.2.5 | Exact rolling-cost attribution | Planned |
| 0.2.6 | Session-scoped process evidence | Planned |
| 0.2.7 | Bounded observation state | Planned |
| 0.2.8 | Tracked governance and review records | Planned |
| 0.2.9 | Width-safe, sanitized rendering | Planned |
| 0.2.10 | Hermetic installed-renderer evidence | Planned |
| 0.2.11 | Isolated self-test and safe diagnostics | Planned |
| 0.2.12 | Documentation, pinned workflow, and public-readiness closure | Planned |
| 0.3.0 | Production-ready milestone | Planned after the patch train |

0.2.1 through 0.2.3 are tagged and released. 0.2.4 is active on this branch;
its implementation components and release records have independent exact-SHA
acceptance, and its aggregate RC has passed the complete local owner gate plus
an isolated Python 3.9 pre-release-wheel proof. Independent aggregate review,
the tag, hosted evidence, and exact tagged-artifact installation proof remain
pending. Nothing in 0.2.5 and later is present, and a later release's evidence
can never stand in for an earlier tag's.

## 0.2.1 — ownership-safe installation

Released:

- Preserve unrelated settings, hook events, groups, matchers and their order.
- Fail closed on unreadable, malformed, non-object, or non-UTF-8 configuration
  before any mutation on both the install and uninstall paths.
- Remove only configuration whose command exactly matches what this installer
  writes; preserve a status line, hook, or checkout symlink whose ownership
  cannot be proven.
- Honour `CLAUDE_CONFIG_DIR`, including paths containing spaces.
- Publish atomically through a symlink with the resolved target's mode, confined
  to the configuration directory, backing up first and leaving no temporary file
  behind on failure.
- Keep reinstallation idempotent.

## 0.2.2 — locked local quality gate

Released:

- A committed `uv.lock`, a `uv >=0.12` requirement, and dependency-group
  development tools.
- Pre-commit hooks for repository hygiene, Ruff, Black, and mypy, run from the
  locked environment; the external `pre-commit-hooks` repository is pinned to
  an immutable commit.
- Subprocess-aware pytest coverage and build configuration.
- Only the mechanical formatting and typing corrections needed for the exact
  v0.2.1 source to pass the declared gate; no behavior change.

## 0.2.3 — malformed host-input resilience

Released:

- Require decoded payload and transcript rows to have mapping shape before
  field access; use the established fallback or skip unsupported rows.
- Validate path, sequence, permission-mode, and session-identifier shapes before
  passing them to filesystem, mapping-key, or sequence operations.
- Reject unsupported transcript conversation identifiers and tool names before
  they can poison incremental or accounting state, including cached roots from
  an earlier run.
- Normalize host-derived numbers through bounded finite integer/fractional
  helpers while preserving accepted numeric strings and exact integers.
- Protect payload, transcript, reset-time, and formatter boundaries from
  invalid, non-finite, and oversized values without emitting `nan` or `inf`.
- Keep absence distinct from zero where it carries meaning, especially payload
  cost, and preserve all ten labels, their order, and valid display output.

## 0.2.4 — private, serialized runtime state

Assembled and locally release-gated on this branch; independent aggregate
acceptance remains pending:

- Route package-owned ledger, transcript, probe, payload, hook, and rate-history
  state through one dependency-free storage service.
- Serialize each file's complete read-modify-write transaction with a private
  sidecar lock; append rate-history records under the same lock.
- Publish replacement files through unique private same-directory temporaries,
  preserving prior bytes and cleaning up the attempted temporary on ordinary
  failure.
- Refuse final symlink and non-regular state or lock entries, keep direct state
  names inside the once-resolved root, and apply `0700` to roots the package
  creates and `0600` to package-owned state and lock files.
- Normalize malformed nested package caches while preserving valid siblings,
  monotonic transcript progress, probe fallback behavior, and exact computed
  ledger aggregates.
- Preserve all ten rows, valid output, and the existing accounting model. This
  release adds no v0.2.5 cost-event or attribution semantics.
