# ADR 0023: Use a locked local quality gate

- Status: Accepted
- Date: 2026-08-29

## Context

The package had pytest and Ruff configuration but no lockfile, coverage
measurement, formatter, type checker, or commit-time gate. CI installed moving
tool versions directly from package indexes, and the first broad repository
review found destructive installer behavior despite a green suite.

Hosted Actions are also temporarily unavailable because the private-account
allowance is exhausted. Local evidence must be reproducible rather than weaker
while hosted evidence is paused.

## Decision

Use uv for the development environment and commit `uv.lock`. Keep Hatchling and
hatch-vcs as the standards-based build backend and Git-tag version source.

The committed pre-commit gate runs repository hygiene checks, Ruff, Black, and
mypy from the locked environment. Release review additionally runs pytest with
subprocess-aware coverage and builds both distributions. Runtime dependencies
remain empty.

Dynamic external JSON makes full strict typing a staged goal. Mypy initially
checks every function body with strict optional, equality, unreachable-code,
and warning policies; typed boundaries are expanded as host payload contracts
are isolated instead of disguising untyped dictionaries with casts.

## Consequences

The same tool versions and commands run locally, in future CI, and during
release verification. Formatting is no longer exempted for dense render code;
source layout is not part of the status-line output contract. Coverage is
review evidence rather than a vanity percentage and must accompany behavior
changes.
