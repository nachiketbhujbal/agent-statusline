# ADR 0037: Require one aggregate public CI result

- Status: Accepted
- Date: 2026-09-11

## Context

[ADR 0033](0033-pin-lean-ci-and-separate-public-conversion.md) requires public
`main` to accept changes only through pull requests with required CI checks.
The always-on `checks` job proves ancestry and, for full-scope changes, policy,
lint, build, installation, and artifact boundaries. The supported-Python tests
run later as a conditional matrix. Requiring `checks` alone would therefore
allow a code pull request to merge while a matrix job was pending or failed.

Requiring each expanded matrix context is also wrong: documentation-only work
deliberately skips the matrix before expansion, so those context names do not
exist and the pull request would remain blocked.

## Decision

Publish one stable `required` CI job after `checks` and `test`. It runs even
when a dependency fails or is skipped. It succeeds only when:

- `checks` succeeded; and
- the Python matrix succeeded for a full-scope change, or the matrix was
  skipped for a documentation-only change.

The scope output is an enum, not a truthiness hint: only exact `true` and exact
`false` are accepted. A missing or unknown value fails the aggregate job. The
scope step must emit both values on its deliberate branches, and the aggregate
job condition must be exactly `if: always()`. Its enforcement script enables
its own fail-fast shell behavior, and the enforcement step may not override its
shell, add a step-level condition, or use `continue-on-error`.
The policy recognizes quoted and whitespace-varied spellings of those YAML
keys, so equivalent syntax cannot bypass the semantic prohibition.

Enforce the job's dependency and result inputs in the local public-readiness
policy. Active repository ruleset `22966865` targets only `main`, has no bypass
actors, requires pull requests and resolved review threads, requires the strict
`required` context from GitHub Actions, and blocks deletion and force-push.

## Consequences

Branch protection has one stable status name while still covering every
required hosted lane. Documentation-only changes retain the inexpensive
always-on ancestry audit without allocating the Python matrix. Hosted macOS
remains opt-in and is not a required pull-request context.

Failing closed on scope drift prevents a removed or malformed job output from
silently converting a full change into an accepted documentation-only skip.

The repository remains usable by one maintainer: pull requests are mandatory,
but GitHub-account approvals are not, because the independent exact-SHA review
is performed outside the author's worktree and recorded in the project review
ledger.
