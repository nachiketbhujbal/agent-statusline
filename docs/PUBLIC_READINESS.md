# Public-readiness audit

This document records the reproducible boundary for the protected public
repository. It contains no machine-local evidence, exact
private billing measurements, personal email address, or unreachable-object
identifier.

## Current verdict

**Complete: the repository is public and `main` is protected by an active,
API-verified no-bypass ruleset.**

The completed baseline retains the accepted historical pull-ref exposure below.
Repository ruleset `22966865` targets only `refs/heads/main`, is active, has no
bypass actors, requires pull requests and resolved review threads, requires the
strict GitHub Actions `required` result, and blocks deletion and non-fast-forward
updates. The API reports the repository as public and `main` as protected.

The ADR 0034 cutover atomically rewrote all 21 intended ordinary branch and tag
refs. A fresh fetch limited to ordinary heads and tags passes the complete
reachable-history audit. Existing v0.2.4 through v0.2.11 Release assets match
the independently verified artifacts built from the rewritten tags.

GitHub still retains twelve provider-managed historical pull heads. Together
they reach 79 old commits, including 11 prior-identity commits and one
superseded private-billing blob. None of their pull-request diffs changed the
private ADR path, but a deliberate fetch can still retrieve the refs. The
maintainer accepted that bounded exposure in [ADR 0035](adrs/0035-accept-historical-pull-refs-and-gate-future-ancestry.md)
rather than replace the repository. Claims below therefore distinguish clean
ordinary refs from the accepted historical pull namespace.

Unreachable commit objects are deliberately outside this audit. The maintainer
accepted that boundary for this migration and will consider those objects
separately. No GitHub Support request is planned.

## Prevention already established

- GitHub web operations use the maintainer's ID-based no-reply address.
- GitHub blocks command-line pushes whose newest commit exposes a private
  account email.
- This checkout has a repository-local no-reply identity and refuses guessed
  identities.
- Every pull request and `main` push audits the complete ancestry of `HEAD`,
  including documentation-only changes. Only the minimal ancestry job runs for
  documentation-only refs; the full gate remains conservatively skipped.
- One stable `required` job waits for the always-on policy job, the complete
  Linux Python matrix, and representative macOS evidence. Full scope requires
  both hosted test lanes to pass; documentation-only scope requires both to be
  deliberately skipped. The `main` ruleset requires that aggregate result from
  the GitHub Actions application against current `main`.
- Only explicit `true` and `false` scope outputs are valid. Missing or malformed
  scope fails closed. Repository policy requires the aggregate job's exact
  unconditional condition and its self-contained fail-fast script, and forbids
  making the enforcement step conditional, non-blocking, or shell-overridden.
  Only reviewed canonical direct keys are accepted on the job and step; quoted,
  escaped, whitespace-varied, duplicate, or unexpected keys fail closed.
- Automatic `main` CI also validates the generated release-spine commit
  identity when the full gate applies.
- Release validates the annotated tagger and peeled commit identities before
  testing, building, or publishing, and audits the tagged commit's ancestry.
- Package-index publication is separate from tag-triggered build and GitHub
  Release creation. Paired manual TestPyPI and PyPI workflows require an
  annotated release tag reachable from exact `main`, download and revalidate
  that existing release pair without rebuilding, and pass only the hash-bound
  files into a dedicated environment-gated job with short-lived OIDC identity.
  A read-only dependent job proves exact index filenames and hashes before an
  isolated Python 3.9 wheel self-test.
- `scripts/verify_public_readiness.py` rejects missing private-root ignores,
  mutable workflow action refs, the undefined dependency prefix, drift from the
  lean CI, two-job release, or separated three-job promotion boundaries, excess
  package-index authority, stored
  publisher credentials, and exact billing evidence in the current ADR.
- `scripts/verify_artifacts.py` rejects private paths and private textual
  evidence from wheel and source-distribution contents, and fails closed rather
  than skipping a regular member above the bounded audit size.
- `scripts/audit_reachable_history.py` audits local, `origin`, and tag refs—or
  an explicitly selected ref and its ancestry—for private paths, exact billing
  evidence, personal-provider email content, non-no-reply identities, and any
  blob above the bounded audit size.

## Completed rewrite evidence

Before remote ref changes, a private offline bundle preserved and recorded its
permissions, object verification result, checksum, and exact included refs.
The transformation ran in a disposable mirror and produced an old-to-new
mapping for every changed branch, commit, and annotated tag object.

The rehearsal and cutover proved all of the following:

1. every intended current branch and release tag is accounted for;
2. no backup, mirror, pull-request, or temporary ref is in the push set;
3. each mapped tree is identical except for the approved ADR 0018
   generalization;
4. commit and tag identities use approved no-reply addresses;
5. the reachable-history audit passes;
6. the release-equivalent local gate passes at rewritten `main`;
7. every rewritten release tag peels to the mapped release commit and reports
   its original version; and
8. one independent reviewer accepts the exact rewritten candidate and mapping.

The rewritten candidate passed the full local gate and one independent review
before cutover. The post-cutover ancestry prevention change creates a new
candidate and therefore requires a renewed exact-SHA review.

## Completed remote cutover

After explicit maintainer authorization, both workflows were suspended, all 20
changed or new refs were applied in one atomic push with exact old-value leases,
and the complete 21-ref ordinary namespace was verified. The twelve accepted
pull refs were separately required to retain their exact inventoried values.
The existing Releases were reconciled against their rewritten tags from private
rollback-backed artifacts before workflow restoration.

The [historical Actions exposure inventory](ACTIONS_EXPOSURE_INVENTORY.md)
downloaded and scanned all 41 retained log archives and all 26 then-retained
artifacts. No log matched the private-evidence policy. Sixteen source-
distribution artifacts contained the superseded ADR 0018 billing phrase and
were deleted with explicit maintainer authorization. A complete second pass
found all 41 logs available and clean and all ten remaining artifacts available
and clean. Workflow runs and logs, GitHub Releases, release assets, refs, and
tags were not deleted or rewritten.

Public conversion and ruleset activation were completed as the final v0.2.13
public-baseline operation. Any orphan-object work remains separate.

v0.2.14 then proved the public operating model on both supported platforms:
automatic pull-request and merged-main runs passed the complete Linux Python
matrix, representative macOS tests and native memory probe, and the stable
aggregate result. Its tag-triggered Release and freshly downloaded artifacts
also passed. That evidence closes the final hosted prerequisite for declaring
v0.3.0 the supported production-ready baseline.

## Completed public baseline

The maintainer explicitly authorized public conversion and `main` protection.
GitHub reports the repository as public, ruleset `22966865` as active with no
bypass actors, and `main` as protected. The ruleset requires pull requests,
resolved review threads, and the strict `required` GitHub Actions context while
blocking branch deletion and force-push. The accepted ADR 0035 pull-ref caveat
and the separately deferred unreachable-object boundary remain unchanged.
