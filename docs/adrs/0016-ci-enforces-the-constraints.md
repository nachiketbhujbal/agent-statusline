# ADR 0016: Enforce the project's constraints in continuous integration

- Status: Accepted; matrix and triggers superseded by [ADR 0018](0018-budget-hosted-ci.md)
- Date: 2026-08-26

## Context

Several decisions here are easy to violate accidentally and invisible in review:
adding a dependency, breaking the install path, or breaking an older Python.
Documentation alone does not stop any of them.

## Decision

CI runs Ruff, the test suite across Linux and macOS on Python 3.9 through 3.13,
a build, a job that fails if `project.dependencies` is non-empty, and a smoke
job that installs into a scratch config directory, asserts the settings wiring,
renders a payload, and uninstalls.

## Consequences

ADR 0004 and ADR 0003 are enforced rather than trusted. Formatting is
deliberately not gated: the render modules are written densely so each row reads
as one unit, and an advisory check that can never pass is only noise. Lint rules
are enforced; layout is not.

## Partially superseded

[ADR 0018](0018-budget-hosted-ci.md) keeps every guard named here but
changes how they are scheduled: the Linux/macOS cross-product becomes Linux-only
with hosted macOS on request, and the four single-purpose jobs are combined.
What CI enforces is unchanged; what it costs is not.
