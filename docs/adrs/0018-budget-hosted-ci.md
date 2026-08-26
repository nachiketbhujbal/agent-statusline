# ADR 0018: Budget hosted CI around private-repository Actions billing

- Status: Superseded by [ADR 0033](0033-pin-lean-ci-and-separate-public-conversion.md)
- Date: 2026-08-26
- Supersedes the matrix and trigger portions of [ADR 0016](0016-ci-enforces-the-constraints.md)

## Context

A measured account-level investigation on 2026-08-26 found that a broad matrix
could consume a material share of a private account's shared Actions allowance
in a short burst. Exact account measurements remain private because they are not
needed to explain the engineering decision.

Two billing mechanics caused it, and neither is visible in elapsed time. Private
repositories are billed per **job**, rounded up to a whole minute, so a short
job can still consume a complete billed unit. Hosted macOS also carries a much
higher multiplier than Linux, making it the dominant cost in a cross-platform
matrix.

The workflow written under ADR 0016 crossed five Python versions with two
operating systems and added four single-purpose Linux jobs. It paid repeated
setup and rounding overhead on every direct push.

## Decision

Test the full supported Python range on hosted Linux only. Do not cross
operating systems with Python versions.

Treat hosted macOS as exceptional: it is off by default and requested through
`workflow_dispatch`, for a `vX.Y.0` release candidate or a change to the
macOS-specific probes. Before requesting one, check the account billing ledger
rather than this repository's run list, because the allowance is shared with
every other private repository.

Combine work that needs no isolation into a single job, so setup overhead and
the per-job minimum are paid once. Python-version isolation is kept because it
is the point of that matrix. Every job carries a ten-minute timeout, and
documentation-only pushes are filtered out with `paths-ignore`.

## Consequences

A default push uses one combined policy/build job plus the five-version Linux
matrix while keeping full Python coverage, both install shapes, the dependency
guard, lint, and the build.

macOS regressions are no longer caught automatically. That is the accepted
trade: the only platform-specific code is the memory probe in `probes.py`, and
the dispatch job asserts it returns real data when it runs.

The lean shape should remain useful if the repository becomes public. The
public-transition, immutable-action, and current trigger decisions are defined
by ADR 0033.
