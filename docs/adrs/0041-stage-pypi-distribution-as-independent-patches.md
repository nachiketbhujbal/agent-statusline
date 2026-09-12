# ADR 0041: Stage PyPI distribution as independent patches

- Status: Accepted
- Date: 2026-09-12

## Context

The project already produces a standard pure-Python wheel and source archive
with Hatchling, derives versions from immutable Git tags, supports Python 3.9
through 3.13, and has no runtime dependencies. It is installed most safely as
an isolated command, but that isolation is a package-manager policy rather than
a custom distribution format: `uv tool`, `pipx`, and `pip` can all consume the
same artifacts.

Publishing introduces several independently useful and differently risky
surfaces. Public metadata and long-description links can be made package-index
ready without changing release authority. Building once and promoting exact
artifacts can harden GitHub Releases without granting package-index identity.
TestPyPI can prove trusted publication before an irreversible production name
and filename boundary is crossed.

Combining those surfaces in one patch would make documentation cleanup,
release-pipeline privilege separation, external account configuration, and the
first production publication one review and rollback unit.

## Decision

Ship the work as four sequential patches:

1. v0.3.2 prepares standard project URLs, portable README rendering, and clear
   package-manager guidance without changing workflows or publishing.
2. v0.3.3 builds and validates one exact wheel/source pair, transports it as one
   named workflow artifact, and gives only the GitHub Release job repository
   write permission.
3. v0.3.4 adds a dedicated, manually approved TestPyPI trusted-publishing job
   and verifies the published hashes, version, and isolated renderer evidence.
4. v0.3.5 adds a separate manually approved production trusted-publishing job,
   verifies the production distribution, and makes package-name installation
   current.

Use no package-index API token. Grant OIDC identity only to the job that needs
it, bind each index to its own protected environment, and keep the build job
read-only. Continue to pin third-party actions to immutable commits. A released
or published mistake is corrected in a later patch rather than by moving a tag
or replacing an uploaded filename.

Recommend `uv tool install` because it isolates a frequently invoked command.
Document `pipx install` as an equivalent isolated option and `pip install` as a
supported environment-scoped option. Do not imply that uv is a runtime
dependency or that package-name installation exists before production
publication succeeds.

Defer host-acquisition architecture and Codex evidence research to the next
minor-development track so it is not coupled to distribution infrastructure.

## Consequences

Each release has one primary purpose and an independently reviewable permission
boundary. v0.3.2 and v0.3.3 require no package-index account or credential.
External account setup begins only when the reviewed v0.3.4 workflow identity
is ready, minimizing the interval in which an unclaimed project name or stale
publisher record can exist.

The first package-name installation will be v0.3.5 rather than a retrospective
upload of an older tag. Until then, immutable tagged-Git installs remain the
documented supported path. `tox` is not introduced: the existing hosted Python
3.9 through 3.13 matrix already supplies interpreter coverage, and PyPI does not
require a particular test orchestrator.
