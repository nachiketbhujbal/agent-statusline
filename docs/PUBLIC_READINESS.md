# Public-readiness audit

This document records the reproducible boundary between a private release and
an authorized public conversion. It contains no machine-local evidence, exact
private billing measurements, personal email address, or unreachable-object
identifier.

## Current verdict

**Conditional go for a separately authorized public conversion. The ordinary
reachable history, released artifacts, retained Actions surface, and prospective
privacy gates now satisfy the pre-conversion technical boundary.**

This verdict is a recommendation, not authorization to change visibility or
repository settings. It retains the accepted historical pull-ref exposure below
and requires `main` protection to be enabled and API-verified immediately after
conversion before the public baseline is called complete.

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
- Automatic `main` CI also validates the generated release-spine commit
  identity when the full gate applies.
- Release validates the annotated tagger and peeled commit identities before
  testing, building, or publishing, and audits the tagged commit's ancestry.
- `scripts/verify_public_readiness.py` rejects missing private-root ignores,
  mutable workflow action refs, the undefined dependency prefix, drift from the
  lean workflow boundary, and exact billing evidence in the current ADR.
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

Public conversion, ruleset activation, and any orphan-object work remain
separate from the v0.2.12 history cleanup.

## Final public decision

The direct recommendation is to permit a separately authorized public
conversion while explicitly accepting the ADR 0035 pull-ref caveat. Immediately
after conversion, enable a no-bypass `main` ruleset with the intended required
checks and verify it through the GitHub API. Until that post-conversion check
passes, describe the repository as technically ready but not as a protected
public baseline. A passing repository does not itself authorize changing
visibility.
