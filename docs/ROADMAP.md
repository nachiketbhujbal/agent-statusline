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
| 0.2.3 | Malformed host-input resilience | **Active** |
| 0.2.4 | Private, serialized runtime state | Planned |
| 0.2.5 | Exact rolling-cost attribution | Planned |
| 0.2.6 | Session-scoped process evidence | Planned |
| 0.2.7 | Bounded observation state | Planned |
| 0.2.8 | Tracked governance and review records | Planned |
| 0.2.9 | Width-safe, sanitized rendering | Planned |
| 0.2.10 | Hermetic installed-renderer evidence | Planned |
| 0.2.11 | Isolated self-test and safe diagnostics | Planned |
| 0.2.12 | Documentation, pinned workflow, and public-readiness closure | Planned |
| 0.3.0 | Production-ready milestone | Planned after the patch train |

0.2.1 and 0.2.2 are tagged and released. 0.2.3 is active on this branch;
nothing in 0.2.4 and later is present in this repository yet, and a later
release's evidence can never stand in for an earlier tag's.

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

Implemented on this branch:

- Require decoded payload and transcript rows to have mapping shape before
  field access; use the established fallback or skip unsupported rows.
- Validate path, sequence, permission-mode, and session-identifier shapes before
  passing them to filesystem, mapping-key, or sequence operations.
- Normalize host-derived numbers through bounded finite integer/fractional
  helpers while preserving accepted numeric strings and exact integers.
- Protect payload, transcript, reset-time, and formatter boundaries from
  invalid, non-finite, and oversized values without emitting `nan` or `inf`.
- Keep absence distinct from zero where it carries meaning, especially payload
  cost, and preserve all ten labels, their order, and valid display output.
