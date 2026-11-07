# ADR 0059: Verify installer listing before index installation

- Status: Accepted; implementation target v0.5.9
- Date: 2026-11-07
- Extends: [ADR 0045](0045-promote-github-releases-through-separate-package-index-workflows.md)

## Context

Multiple promotions, including v0.5.8, exposed matching release JSON hashes
before the Simple Index listed the new wheel. Publication succeeded but the
clean index install failed with no matching distribution. Verification-only
retries later passed without replacing artifacts or repeating uploads.

## Decision

Within the existing bounded verifier retry loop, require both the versioned
release JSON identity/type/hash checks and the project's Simple JSON listing.
Negotiate `application/vnd.pypi.simple.v1+json` as specified by the
[Simple Repository API](https://packaging.python.org/en/latest/specifications/simple-repository-api/).
The listing must expose exactly one non-yanked entry for each expected filename
with the exact SHA-256. It may also contain other versions. Both PyPI and
TestPyPI use their own fixed endpoints. Retain timeouts, response bounds and
the existing attempt/delay settings.

The dependent clean install and isolated self-test remain necessary: advertised
listing readiness alone does not prove that a CDN download or a client with
different cached evidence will succeed. Exhausted propagation fails verification
with its reason. Retry only failed verification after inspecting evidence;
do not rebuild, replace or repeat a successful upload.

## Consequences

The shared verifier corrects both promotion lanes and the TestPyPI prerequisite
for production without changing their approvals or workflow topology. Network
access remains confined to release tooling; runtime source, display, settings,
ledger and dependencies do not change. Synthetic tests reproduce ready release
metadata with a delayed installer listing, both endpoint paths, bounded failure,
hash/membership checks and yanked files.
