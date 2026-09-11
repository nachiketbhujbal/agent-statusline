# ADR 0035: Accept historical pull refs and gate future ancestry

- Status: Accepted
- Date: 2026-09-11
- Extends [ADR 0034](0034-rewrite-reachable-pre-public-history-once.md)

## Context

The ADR 0034 cutover rewrote every intended ordinary branch and release tag,
but GitHub retains a read-only `refs/pull/<number>/head` namespace for existing
pull requests. Repository owners cannot update or delete those provider-managed
refs. The twelve historical pull heads all retain the superseded private ADR
blob and together reach 79 old commits, including 11 commits with the prior
maintainer identity. None of the pull-request diffs changed the private ADR
path, which limits casual exposure but does not prevent a deliberate ref fetch.

Replacing the repository would remove that namespace but would also discard the
existing repository identity and collaboration record. The maintainer rejected
repository replacement and explicitly accepted this bounded historical
residue. Unreachable objects and provider caches remain outside this decision.

The previous CI path filters also skipped documentation-only pull requests and
`main` changes. That was compatible with a cost-minimizing test gate but not
with an ancestry privacy gate: a documentation-only ref can still introduce an
unsafe ancestor.

## Decision

Retain exactly the twelve existing provider-managed pull heads as accepted
historical exposure. Do not describe the complete provider-visible ref
namespace as sanitized. Public-readiness claims distinguish the rewritten
ordinary branch/tag graph from this accepted pull-ref residue.

Audit the complete ancestry of `HEAD` on every pull request and every push to
`main`, including documentation-only changes. A documentation-only change runs
only this minimal history job; the full lint, test matrix, build, install, and
artifact gate remains skipped to conserve private-repository Actions usage.
Release runs audit the complete ancestry of the tagged commit before tests,
build, or publication.

The repository policy verifier requires full checkout history, the ancestry
audit commands, the unfiltered pull-request and `main` triggers, and the
documentation-only scope gate. It rejects any path filter that could suppress
the ancestry audit. Local release review continues to audit all ordinary local,
origin, and tag refs.

## Consequences

An existing historical pull ref can still be fetched by someone who knows or
discovers its number. That residual privacy exposure is accepted; it is not a
security boundary and is not evidence that ordinary rewritten refs failed.

Every new pull request, merge, and release is blocked if its complete ancestry
contains a disallowed identity, private path, personal-provider email, or exact
private billing evidence. Old local clones must still be reconciled before
contributing so they cannot reintroduce superseded history under a new ref.

The minimal ancestry job consumes one Linux job for documentation-only refs.
That is the smallest hosted cost that preserves the always-on boundary while
the repository remains private.
