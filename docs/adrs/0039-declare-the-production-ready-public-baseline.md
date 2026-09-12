# ADR 0039: Declare the production-ready public baseline

- Status: Accepted
- Date: 2026-09-12

## Context

ADR 0030 replaced a proposed monolithic v0.3.0 hardening release with small,
independently reviewable patches. v0.2.1 through v0.2.14 have now been released
sequentially. Together they cover installation ownership, reproducible quality
gates, hostile-input resilience, private serialized state, exact rolling-cost
attribution, session isolation, bounded observations, tracked governance,
terminal-safe rendering, installed-artifact evidence, isolated diagnostics,
history and artifact privacy, protected public conversion, and automatic Linux
and macOS CI.

The old `codex/hardening/v0.3.0-production-readiness` integration branch predates
that train. It is useful historical source material, but its changes have been
extracted, corrected, reviewed, and superseded by the released mainline. Merging
it now would reintroduce obsolete implementations and records.

Every patch has an immutable annotated tag and release-specific artifact proof.
GitHub Release objects begin at v0.2.4, when hosted CI and Release were enabled;
v0.2.1 through v0.2.3 were independently built and installed locally instead.

## Decision

Release v0.3.0 as the explicit production-ready supported public baseline. The
milestone changes only version-boundary documentation, immutable-tag installation
and upgrade guidance, and the package maturity classifier from `Beta` to
`Production/Stable`. It does not merge or cherry-pick the historical integration
branch and does not change runtime source, renderer behavior, approved rows or
fields, dependencies, installation behavior, workflows, state, or live wiring.

`Production/Stable` states that this release is suitable for normal supported
use. The project remains pre-1.0: semantic-versioning compatibility rules still
permit a future 0.x minor to make explicitly documented incompatible changes.
This decision does not publish to PyPI; immutable public Git tags remain the
normal installation source until a separate publication decision is accepted.

## Consequences

- Users can install and explicitly advance the supported baseline as a normal
  local command from an immutable Git tag without cloning the repository.
- The complete patch train, rather than the obsolete integration branch, is the
  auditable history of how the supported baseline was built.
- Future runtime, performance, host-architecture, PyPI, historical-ref, orphan,
  or live-installation work requires its own scoped roadmap entry and release.
- The milestone must still pass the complete local gate, independent exact-SHA
  review, protected hosted CI, annotated tag, Release, and downloaded-artifact
  verification; prior patch evidence does not replace those final checks.
