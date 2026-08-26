# ADR 0004: Ship no runtime dependencies

- Status: Accepted
- Date: 2026-08-26

## Context

The status line is spawned as a fresh process several times a second, on
whatever Python the machine happens to have. A third-party import would add
cost to every redraw and an install step to every new machine, on a tool whose
entire value is being present without ceremony.

## Decision

`project.dependencies` stays empty and the code uses only the standard library.
`install.py` is stdlib-only as well, since it is the script that runs before
anything is installed.

## Consequences

`pip install` is optional and only adds console scripts to PATH; the status line
runs straight from a checkout. Continuous integration fails the build if
dependencies are ever added, so the constraint is enforced rather than
remembered. Development tooling lives in an optional `dev` extra.
