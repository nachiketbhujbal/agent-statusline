# ADR 0019: Treat release tags as immutable

- Status: Accepted
- Date: 2026-08-26

## Context

Six release workflow runs were triggered for three version names, because
`v0.1.0` and `v0.1.1` were each pushed more than once while history was being
corrected. Beyond the wasted runs, a moved tag makes a published version name
ambiguous: an artifact built from it cannot be traced to one commit.

A separate one-time exception did occur. Purging personal data from the
repository required deleting every tag and its release, because release sdists
carried the removed content. That purge is complete and closed.

## Decision

Once pushed, a version tag is never moved, deleted, or reused. A mistake in a
released version is corrected by a new patch version.

A tag is created only on a commit that has already been verified, so the tag
workflow is post-tag evidence rather than the thing that decides whether the
release is good. If tag automation fails, the cause is fixed in a new version.

## Consequences

Every version name maps to exactly one commit permanently, and a released
artifact can always be traced back to it. Version numbers are consumed slightly
faster, which is the intended trade.

`v0.1.0` and `v0.1.1` are burned and must never be reissued, even though no tag
of either name currently exists.
