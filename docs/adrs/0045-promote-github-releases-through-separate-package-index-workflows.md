# ADR 0045: Promote GitHub Releases through separate package-index workflows

- Status: Accepted
- Date: 2026-09-13
- Supersedes: the package-index workflow topology in ADR 0043

## Context

ADR 0043 proved trusted TestPyPI publication by extending the tag-triggered
Release workflow. That first deployment safely reused the build job's
SHA-bound artifact, but it also made every new tag wait at a TestPyPI approval
gate and left no equally bounded path for promoting an already published
GitHub Release to production PyPI.

Production publication is an irreversible package-name and filename boundary.
It must not rebuild a tag, accept a stored API token, upload ambient files, or
gain authority merely because a Git tag was pushed. TestPyPI and PyPI also use
different trusted-publisher identities and GitHub environments; their workflow
filenames should make that distinction explicit.

The v0.3.5 wheel and source archive already passed the locked build, GitHub
Release, TestPyPI hash verification, and isolated Python 3.9 installation. A
production promotion should preserve those exact bytes rather than manufacture
a second build after the tag.

## Decision

Keep `release.yml` responsible only for the tag-triggered build and GitHub
Release. Add paired, manually dispatched `publish-testpypi.yml` and
`publish-pypi.yml` workflows. Each accepts one exact `vMAJOR.MINOR.PATCH` tag,
runs only from `main`, requires an annotated tag reachable from that exact main
revision, and downloads the existing release's wheel and source archive.

The unprivileged preparation job requires exactly the expected two filenames,
rechecks distribution contents and package-description rendering, records both
SHA-256 identities, and transfers the pair through a one-day GitHub Actions
artifact bound to the tagged commit. It never builds a distribution.
Production preparation additionally requires TestPyPI to report that exact
project, version, filename pair, distribution types, and hashes before PyPI can
receive authority.

Only the two-action publish job receives `id-token: write`. It downloads the
named artifact from the same workflow run and invokes the immutable-pinned PyPA
publisher inside the corresponding manually approved `testpypi` or `pypi`
environment. It performs no checkout, script execution, build, credential
lookup, cross-run download, or collision skip. Trusted-publisher records bind
the repository, exact workflow filename, and environment; no long-lived PyPI
secret exists.

A dependent read-only job requires the package index to report exactly the
prepared project, version, wheel, source archive, distribution types, and
SHA-256 values within a finite retry window. It then installs the exact wheel
with no dependencies or source fallback in a fresh Python 3.9 environment,
checks the command version, and runs the self-test against disposable state.

Static policy and synthetic mutations lock both workflows' trigger, input,
main/tag provenance, job topology, permissions, environment, endpoints,
artifact transport, action inputs, bounded verification, isolated install, and
absence of credentials, conditional evidence, or rebuild commands.

For the already released v0.3.5, the successful TestPyPI deployment from the
old topology remains valid and is not repeated. Production uses the new
`publish-pypi.yml` workflow to promote the exact existing GitHub Release pair.

## Consequences

Tag creation and GitHub Release publication no longer imply package-index
publication. Each index requires an explicit dispatch and its own human
environment approval, keeping accidental and duplicate uploads conservative.

The workflow implementation may land after the immutable v0.3.5 tag while
still safely promoting v0.3.5: workflow authority and verification come from
reviewed `main`, while artifact identity and version come from the existing
annotated tag and GitHub Release. Future releases use the same separated lanes.

TestPyPI's trusted-publisher record must be updated from `release.yml` to
`publish-testpypi.yml` before a future TestPyPI promotion. Production PyPI is
bound directly to `publish-pypi.yml` and the `pypi` environment.

Runtime source, dependencies, the approved ten-row display, accounting, local
state, live Claude Code configuration, and Codex host behavior do not change.
