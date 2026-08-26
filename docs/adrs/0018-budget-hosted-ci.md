# ADR 0018: Budget hosted CI around private-repository Actions billing

- Status: Accepted
- Date: 2026-08-26
- Supersedes the matrix and trigger portions of [ADR 0016](0016-ci-enforces-the-constraints.md)

## Context

A measured account-level investigation on 2026-08-26 reconciled the GitHub Free
allowance exactly: 2,000.3 Linux-equivalent minutes across two private
repositories, of which this one consumed 21.83 percent in about 52 minutes.

Two billing mechanics caused it, and neither is visible in elapsed time. Private
repositories are billed per **job**, rounded up to a whole minute, so a job that
finishes in ten seconds still bills a minute. And hosted macOS is accounted at
roughly 10.33 times the Linux rate, so macOS was 25.55 percent of the actual
minutes but 78 percent of the allowance consumed.

The workflow written under ADR 0016 crossed five Python versions with two
operating systems and added four single-purpose Linux jobs, giving 14 jobs on
every direct push — about 59 billed minutes per run to do a few minutes of work.

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

A default push falls from 14 jobs and about 59 billed minutes to 6 jobs and
about 6 — roughly a 90 percent reduction — while keeping full Python coverage,
both install shapes, the dependency guard, lint, and the build.

macOS regressions are no longer caught automatically. That is the accepted
trade: the only platform-specific code is the memory probe in `probes.py`, and
the dispatch job asserts it returns real data when it runs.

Public repositories get unlimited free minutes, so this constraint disappears if
this repository becomes public. The lean shape should be kept anyway; a
superseding ADR may relax the macOS gate at that point.
