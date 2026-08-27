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
| [0020](0020-own-only-managed-configuration.md) | Mutate only managed configuration |
| [0021](0021-lock-and-privatize-runtime-state.md) | Lock and privatize runtime state |
| [0022](0022-account-rolling-costs-with-timestamped-deltas.md) | Timestamped rolling-cost accounting |
| [0023](0023-use-a-locked-local-quality-gate.md) | Locked local quality gate |
| [0024](0024-scope-process-probes-by-session.md) | Session-scoped process probes |

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
