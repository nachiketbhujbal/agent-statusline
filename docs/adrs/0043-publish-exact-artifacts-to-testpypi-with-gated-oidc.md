# ADR 0043: Publish exact artifacts to TestPyPI with gated OIDC

- Status: Accepted
- Date: 2026-09-13

## Context

ADR 0042 separated the tag-triggered build from GitHub Release publication and
bound one wheel/source pair to exact filenames and SHA-256 hashes. It granted no
package-index authority. The next release must prove the external publication
contract without exposing a long-lived token or coupling the first test upload
to the irreversible production package-name boundary.

Trusted publishing exchanges GitHub's short-lived OpenID Connect identity for a
single upload. That identity is useful only if its repository, workflow, and
environment claims exactly match a TestPyPI publisher record. Granting identity
at workflow or build scope, rebuilding in the privileged job, accepting ambient
files, or silently skipping an existing filename would weaken the artifact and
immutability guarantees already established.

TestPyPI may also expose a newly uploaded release after a short propagation
delay. A successful upload alone therefore does not prove that the public index
reports the reviewed files or that a user can install the supported wheel.

## Decision

Add a `testpypi` GitHub environment with a required manual maintainer approval
and no deployment bypass. Configure TestPyPI's pending trusted publisher for the
exact `nachiketbhujbal/agent-statusline`, `.github/workflows/release.yml`, and
`testpypi` identity only after the workflow candidate has passed independent
exact-SHA review. The environment permits tag deployments and remains distinct
from the future production environment.

Keep the build and GitHub Release jobs from ADR 0042. A later
`testpypi-publish` job depends on both, downloads their SHA-bound artifact, and
invokes the immutable-pinned PyPA publish action. That job has exactly
`id-token: write`, performs no checkout, build, script execution, or credential
lookup, targets only TestPyPI, and does not use `skip-existing`. No API token or
package-index secret is stored.

A read-only dependent job polls the version-specific TestPyPI JSON endpoint at
a fixed finite attempt, delay, response-size, and request-timeout bound. It
requires the exact project/version, exactly the expected wheel and source
archive, their build-job SHA-256 values, and their distribution types. It then
creates a fresh Python 3.9 virtual environment, installs the exact wheel from
the TestPyPI index with no dependencies or source-build fallback, verifies the
command version, and runs the installed self-test with disposable state.

Policy tests lock the four-job topology, dependency order, environment,
least-privilege permissions, action identity, TestPyPI endpoints, exact artifact
binding, bounded verification, isolated install, and absence of stored
credentials or bypass controls. A tag or uploaded filename is immutable; any
failure requiring a content change is corrected in a later patch.

Production PyPI remains v0.3.5. This decision changes no runtime source,
runtime dependency, display, accounting, live configuration, or Codex host
behavior.

## Consequences

The first package-index publication is deliberately a manually approved test
deployment. The user must approve the environment gate; automation cannot turn
that human decision into a token-bearing or self-approved step. GitHub Release
must succeed before the TestPyPI deployment can begin.

TestPyPI propagation can consume up to the documented retry window, but cannot
loop indefinitely or convert partial index state into a passing result. Exact
hash and installed-wheel evidence closes the gap between an accepted upload and
a usable distribution while leaving production name acquisition and normal
package-name installation claims untouched.
