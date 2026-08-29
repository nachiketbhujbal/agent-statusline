# ADR 0030: Ship hardening as small pre-1.0 patches

- Status: Accepted
- Date: 2026-08-28

## Context

A shared integration branch accumulated installation, storage, accounting,
probe, rendering, test-evidence, diagnostics and documentation changes under one
proposed minor release. Although they share a broad safety goal, one release
would be difficult to review, bisect, explain, or roll back. The project is
pre-1.0 with one primary maintainer, but each tag still needs a clear
compatibility boundary and its own immutable evidence.

## Decision

Ship that work as sequential, single-purpose 0.2.x patches. A patch may contain
compatible fixes and tightly coupled additive diagnostics, but must not remove an
approved row or field, change an existing command incompatibly, or conceal a
breaking change. Each patch gets its own branch, review, gates, pull request,
tag and installed-artifact proof.

Cut each release branch from the preceding released state on `main` and bring
over only that release's cohesive implementation, tests, ADR and documentation.
Keep the integration branch as source material; do not merge it wholesale.

Reserve 0.3.0 as the explicit production-ready milestone after the patch train,
not as a container for unrelated work. `ROADMAP.md` owns future release scope;
`CHANGELOG.md` describes only the next unreleased slice and already-landed tags.

## Consequences

- Review and rollback boundaries are smaller and map directly onto tags.
- A later release's evidence cannot substitute for proving an earlier artifact.
- Preparing the train requires deliberate commit selection instead of one merge.
- Compatible additions may appear in a pre-1.0 patch, but incompatible behavior
  still requires an explicitly planned minor boundary.

## Evidence

`ROADMAP.md` maps 0.2.1 through 0.2.12 to one primary purpose each and marks
only 0.2.1 as implemented. `CHANGELOG.md` contains only the 0.2.1 slice above
the released 0.2.0 history.
