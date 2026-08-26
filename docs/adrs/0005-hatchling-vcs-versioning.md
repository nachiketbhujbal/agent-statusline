# ADR 0005: Build with Hatchling and derive versions from Git

- Status: Accepted
- Date: 2026-08-26

## Context

Static version strings disagree across source, package metadata, built
artifacts, and tags, and the disagreement is usually discovered at release time.

## Decision

Use Hatchling with hatch-vcs. Annotated `vX.Y.Z` tags are authoritative;
`_version.py` is generated at build time and gitignored, and no editable version
string exists in the source.

## Consequences

Tagging is part of releasing, not a step after it. Untagged builds receive a PEP
440 development version. `agent_statusline.__version__` falls back to
`0.0.0.dev0` when imported from a checkout that was never built.
