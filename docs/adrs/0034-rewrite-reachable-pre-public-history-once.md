# ADR 0034: Rewrite reachable pre-public history once for privacy

- Status: Accepted
- Date: 2026-09-11
- Creates one bounded exception to [ADR 0019](0019-release-tags-are-immutable.md)

## Context

The repository remains private, but its reachable history contains exact
private-account billing measurements that are unnecessary to the product or
the lean-CI decision. Release-spine merge commits also used a personal
maintainer author identity because the web-operation privacy setting was not
enabled. Editing only the current files would leave those values in earlier
commits, tags, source archives, and release provenance.

ADR 0019 normally forbids moving a published version tag. Keeping that rule
without exception would require accepting the private historical data or
replacing the repository. The maintainer rejected replacement and authorized a
recoverable in-place rewrite of reachable refs before public conversion.

## Decision

Perform one deterministic pre-public migration that rewrites every intended
reachable branch and the release tags from v0.2.1 through v0.2.11. Replace the
single private-billing blob with the approved generalized ADR 0018 text and
normalize affected maintainer commit/tag identities to the ID-based GitHub
no-reply address. Do not otherwise change release trees.

Before any remote mutation:

- freeze repository publication;
- create and verify a private offline bundle containing the original refs;
- perform the transformation in a disposable mirror;
- enumerate the exact remote ref update set and exclude backup, mirror,
  temporary, and pull-request refs;
- produce a complete old-to-new object mapping;
- prove tree equivalence outside ADR 0018;
- pass the reachable-history audit and release-equivalent local gate; and
- obtain one independent exact-candidate review.

The remote cutover uses explicit force-with-lease updates against the inventoried
old ref values, not an unrestricted mirror push. Workflow and protection changes,
tag movement, release repair, and publication require the maintainer's later
approval at that destructive boundary.

Unreachable orphan objects are outside this migration. No GitHub Support purge
is requested. Repository visibility remains a separate authorization boundary.

## Consequences

Every rewritten descendant commit, annotated tag object, and affected artifact
digest receives a new identity. Existing verification records remain truthful
about the original private history, while a private mapping records how each
released state moved. Local clones and worktrees must be reconciled or replaced
after the cutover so an old merge cannot reintroduce the prior history.

This exception ends when the migration is verified. The ordinary ADR 0019 rule
then resumes: future release tags are immutable, and later corrections consume
a new version.
