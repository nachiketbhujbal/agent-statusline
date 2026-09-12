# ADR 0042: Build once and promote exact release artifacts

- Status: Accepted
- Date: 2026-09-12

## Context

The tag-triggered Release workflow built, validated, and published inside one
job with repository-content write permission. It installed current, unbounded
versions of its build and test tools, built into the conventional `dist`
directory, and published every matching path there. The repository gate and
artifact checks made that workflow substantially safer, but they did not prove
that the files handed to the release action were the same pair a separately
privileged stage had validated.

The v0.3.2 release demonstrated a concrete reproducibility gap. Its hosted
source and wheel used Core Metadata 2.5 and passed current Twine 7, while the
Python-3.9-compatible Twine 6 in the local development group could not parse
that metadata version. Both results were internally correct; the mismatch
showed that a moving hosted build toolchain and a differently constrained local
checker were not one reproducible release boundary.

## Decision

Build each tagged release exactly once in a read-only `build` job. Install an
exact uv version, synchronize build and validation tools from the committed
lock, and build without an isolated resolver into a dedicated `release-dist`
directory. Remove uv's known generated output-directory `.gitignore` marker by
its exact path before validation. Keep the existing ancestry, documentation,
public-readiness, test, archive-privacy, and package-description checks in that
job.

Require exactly the tag-version wheel and source archive, reject symlinks or
additional directory members, calculate both SHA-256 digests, and expose only
their filenames, hashes, and a workflow-artifact name bound to the exact commit
SHA. Upload that directory as one short-retention workflow artifact.

Give repository-content write permission only to a dependent
`github-release` job. It downloads the one named artifact, rejects any member,
filename, version, or hash disagreement, and passes the two explicit paths to
the GitHub Release action. It does not install build tools or rebuild.

Enforce this topology with the standard-library public-readiness checker and
synthetic mutations covering permission escalation, dependency removal,
duplicate builds, artifact-name drift, ambient `dist` publication, conditional
evidence, and premature package-index identity permission. Continue pinning all
third-party actions to immutable commits.

## Consequences

The published GitHub Release files are the exact pair validated by the
read-only job, with identities recorded before the write-capable job begins.
The release toolchain is reproducible from `uv.lock`, while runtime dependencies
remain empty and Python 3.9 remains supported by the package itself. Release
tools may require Python 3.10 or newer because the hosted build uses Python
3.12 and those tools do not run in the installed command.

The workflow artifact is transport evidence, not a package-index publication.
TestPyPI, PyPI, OIDC, hosted environments, accounts, and credentials remain
outside this decision and require the later boundaries in ADR 0041.
