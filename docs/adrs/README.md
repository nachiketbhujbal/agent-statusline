# Architecture decision records

Each numbered file records one durable project decision. Accepted records are
append-only history: when a decision changes, add a new ADR that supersedes the
old one rather than rewriting why the earlier choice was made.

| ADR | Decision |
| --- | --- |
| [0001](0001-exactly-accountable-money.md) | Show only exactly accountable money |
| [0002](0002-state-outside-the-repository.md) | Runtime state outside the repository |
| [0003](0003-install-by-one-symlink.md) | Install by one symlink *(superseded by 0017)* |
| [0004](0004-no-runtime-dependencies.md) | No runtime dependencies |
| [0005](0005-hatchling-vcs-versioning.md) | Hatchling and Git-tag versions |
| [0006](0006-cached-probes-only.md) | Cached probes, never direct subprocesses |
| [0007](0007-incremental-transcript-with-versioned-totals.md) | Incremental transcript with versioned totals |
| [0008](0008-observe-the-cache-ttl.md) | Observed, not assumed, cache TTL |
| [0009](0009-suppress-derived-rate-limit-figures-in-overage.md) | Suppressed rate-limit derivations in overage |
| [0010](0010-wrap-then-truncate.md) | Wrap to two lines, then truncate |
| [0011](0011-row-order-is-data.md) | Row order as data |
| [0012](0012-match-the-host-permission-colours.md) | Host-matched permission-mode colours |
| [0013](0013-remove-the-cache-warmth-bar.md) | Removal of the cache warmth bar |
| [0014](0014-never-exercise-cost-paths-against-the-live-ledger.md) | No cost paths against the live ledger |
| [0015](0015-timestamp-hooks-are-a-stopgap.md) | Message-timestamp hooks as a stopgap |
| [0016](0016-ci-enforces-the-constraints.md) | Constraints enforced in CI *(matrix superseded by 0018)* |
| [0017](0017-install-as-a-python-tool.md) | Install as a Python tool |
| [0018](0018-budget-hosted-ci.md) | Hosted CI budgeted around Actions billing |
| [0019](0019-release-tags-are-immutable.md) | Release tags are immutable |
| [0020](0020-own-only-managed-configuration.md) | Own only managed configuration |
| [0021](0021-lock-and-privatize-runtime-state.md) | Lock, atomically publish, and privatize runtime state |
| [0022](0022-account-rolling-costs-with-timestamped-deltas.md) | Account rolling costs with timestamped deltas |
| [0023](0023-use-a-locked-local-quality-gate.md) | Use a locked local quality gate |
| [0024](0024-scope-process-probes-by-session.md) | Scope process probes by session |
| [0025](0025-bound-ephemeral-observation-state.md) | Bound ephemeral observation state |
| [0026](0026-coordinate-one-owner-and-one-reviewer.md) | Coordinate one owner and one reviewer |
| [0027](0027-measure-cells-and-sanitize-terminal-output.md) | Measure cells and sanitize terminal output |
| [0028](0028-gate-the-installed-renderer-with-synthetic-evidence.md) | Gate the installed renderer with synthetic evidence |
| [0029](0029-self-test-with-isolated-state-and-safe-failure-evidence.md) | Self-test with isolated state and safe failure evidence |
| [0030](0030-ship-hardening-as-small-pre-one-patches.md) | Ship hardening as small pre-1.0 patches |
| [0031](0031-practical-local-threat-model.md) | Practical local-tool threat model |
| [0032](0032-normalize-malformed-host-input-at-the-boundary.md) | Normalize malformed host input at the boundary |
| [0033](0033-pin-lean-ci-and-separate-public-conversion.md) | Pin lean CI and separate public conversion |
| [0034](0034-rewrite-reachable-pre-public-history-once.md) | Rewrite reachable pre-public history once for privacy |
| [0035](0035-accept-historical-pull-refs-and-gate-future-ancestry.md) | Accept historical pull refs and gate future ancestry |
| [0036](0036-fail-closed-on-oversized-public-evidence.md) | Fail closed on oversized public evidence |
| [0037](0037-require-one-aggregate-public-ci-result.md) | Require one aggregate public CI result |
| [0038](0038-run-public-ci-on-linux-and-macos.md) | Run public CI on Linux and macOS |
| [0039](0039-declare-the-production-ready-public-baseline.md) | Declare the production-ready public baseline |
| [0040](0040-remove-avoidable-hot-path-imports.md) | Remove avoidable hot-path imports and record non-gating benchmarks |
| [0041](0041-stage-pypi-distribution-as-independent-patches.md) | Stage PyPI distribution as independent patches |
| [0042](0042-build-once-and-promote-exact-release-artifacts.md) | Build once and promote exact release artifacts |
| [0043](0043-publish-exact-artifacts-to-testpypi-with-gated-oidc.md) | Publish exact artifacts to TestPyPI with gated OIDC |

## Reading order

New here, or handing this to another agent? Read [0001](0001-exactly-accountable-money.md),
[0014](0014-never-exercise-cost-paths-against-the-live-ledger.md) and
[0004](0004-no-runtime-dependencies.md) first. They are the three that are
expensive to violate: the first two guard real money, the third guards the
property that makes the tool usable at all.

## Related

- Things that were searched for and do not exist are recorded under
  [dead ends](../INTERNALS.md#dead-ends--already-searched-do-not-redo), not here.
- Ideas considered and consciously not built are in [DEFERRED.md](../DEFERRED.md).
