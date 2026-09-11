# Public-readiness audit

This document records the reproducible boundary between a private release and
an authorized public conversion. It contains no machine-local evidence, exact
private billing measurements, personal email address, or unreachable-object
identifier.

## Current verdict

**No-go for public visibility and no-go for the v0.2.12 tag until the reachable
history rewrite in [ADR 0034](adrs/0034-rewrite-reachable-pre-public-history-once.md)
is complete and independently verified.**

The v0.2.12 working tree removes private billing detail and adds prevention and
audit tooling. That does not remove prior blobs or commit metadata. Current
published refs still reach one unchanged private-billing blob through 99 commit
snapshots, and 12 release-spine merge commits carry a personal maintainer author
identity. The repository remains private.

Unreachable commit objects are deliberately outside this audit. The maintainer
accepted that boundary for this migration and will consider those objects
separately. No GitHub Support request is planned.

## Prevention already established

- GitHub web operations use the maintainer's ID-based no-reply address.
- GitHub blocks command-line pushes whose newest commit exposes a private
  account email.
- This checkout has a repository-local no-reply identity and refuses guessed
  identities.
- Automatic `main` CI validates the generated release-spine commit identity.
- Release validates the annotated tagger and peeled commit identities before
  testing, building, or publishing.
- `scripts/verify_public_readiness.py` rejects missing private-root ignores,
  mutable workflow action refs, the undefined dependency prefix, drift from the
  lean workflow boundary, and exact billing evidence in the current ADR.
- `scripts/verify_artifacts.py` rejects private paths and private textual
  evidence from wheel and source-distribution contents.
- `scripts/audit_reachable_history.py` audits local, `origin`, and tag refs for
  private paths, exact billing evidence, personal-provider email content, and
  non-no-reply commit or tag identities. It intentionally fails before the
  rewrite and must pass afterward.

## Required rewrite evidence

Before any remote ref changes, preserve a private offline bundle and record its
permissions, object verification result, checksum, and exact included refs.
Perform the transformation in a disposable mirror and produce an old-to-new
mapping for every changed branch, commit, and annotated tag object.

The rehearsal must prove all of the following:

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

Any correction changes the candidate and requires renewed exact-SHA review.

## Remote cutover boundary

The remote rewrite is a later, destructive boundary. It requires a separate
maintainer check-in after the offline bundle and rehearsal evidence are
available. At that boundary, workflows and blocking rules are changed only as
explicitly authorized; branches and tags are updated from an enumerated ref
manifest rather than a broad mirror push. Existing Releases and uploaded
artifacts are then reconciled against their rewritten tags before workflows are
restored.

Historical Actions logs and artifacts must be inventoried before public
conversion because GitHub makes private-repository Actions history visible when
the repository becomes public. Public conversion, ruleset activation, and any
orphan-object work remain separate from the v0.2.12 history cleanup.

## Final public decision

After the in-place rewrite, release repair, fresh hosted evidence, and remote
reachable-ref audit all pass, update this document with exact public-safe
evidence and present a new visibility recommendation. A passing repository does
not itself authorize changing visibility.
