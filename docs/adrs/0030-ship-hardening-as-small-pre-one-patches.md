# ADR 0030: Ship hardening as small pre-1.0 patches

- Status: Accepted
- Date: 2026-08-28

## Context

The hardening integration branch accumulated installation, storage,
accounting, probe, rendering, test-evidence, diagnostics, and documentation
changes under one proposed 0.3.0 release. Although they share a broad safety
goal, one release would be difficult to review, bisect, explain, or roll back.
The project is still pre-1.0 and has one primary maintainer, but it still needs
clear compatibility boundaries and immutable evidence for each tag.

## Decision

Ship the integration work as sequential, single-purpose 0.2.x patches. Each
patch may contain compatible fixes and tightly coupled additive diagnostics,
but must not remove an approved row or field, change an existing command
incompatibly, or conceal a breaking change. Each patch receives its own branch,
review, gates, pull request, tag, and installed-artifact proof.

Keep the shared integration branch as source material; do not rewrite or merge
it wholesale. Cut each release branch from the preceding verified tag and bring
over only that release's cohesive implementation, tests, ADR, and documentation.

Reserve 0.3.0 as the explicit production-ready milestone after the patch train,
not as a container for unrelated work. `ROADMAP.md` owns future release scope;
`CHANGELOG.md` describes only the next unreleased slice and already-landed tags;
`RESEARCH.md` retains ideas without a committed release.

## Consequences

- Review and rollback boundaries are smaller and directly reflected by tags.
- Later integration-branch evidence cannot substitute for proving an earlier
  release artifact.
- Preparing the train requires deliberate commit selection instead of one merge.
- Compatible additions may appear in a pre-1.0 patch, but incompatible behavior
  still requires an explicitly planned minor boundary.

## Evidence

`ROADMAP.md` maps 0.2.1 through 0.2.10 to one primary purpose each, while
`CHANGELOG.md` contains only the next 0.2.1 slice above the released 0.2.0
history.
