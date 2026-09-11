# ADR 0033: Pin lean CI and separate public conversion

- Status: Accepted
- Date: 2026-09-11
- Supersedes [ADR 0018](0018-budget-hosted-ci.md)

## Context

ADR 0018 established a deliberately small hosted matrix after a private-account
billing investigation. Its lean design remains sound, but its exact private
measurements do not belong in a repository intended for public visibility. The
workflows also referenced mutable major-version tags, allowing upstream tag
movement to change code executed by CI without a repository change.

The repository is still private and both workflows are active. Hosted evidence
now exists for the patch train, but the current GitHub Free plan does not expose
repository rulesets or branch protection for this private repository. Public
conversion and the settings that should immediately follow it are therefore a
separate operational boundary.

## Decision

Keep the lean workflow shape:

- ordinary CI uses one combined Linux policy/build job and a Linux Python
  3.9–3.13 matrix;
- hosted macOS remains an explicit `workflow_dispatch` option for macOS probe
  changes or a deliberate milestone canary;
- documentation-only changes remain outside automatic CI; and
- release publication remains tag-triggered and Linux-only because the wheel is
  pure Python and platform evidence belongs to CI.

Every third-party workflow action is pinned to a reviewed, full commit SHA with
a readable release comment. A future action update changes both the SHA and its
comment in an ordinary reviewed pull request. Repository policy rejects moving
tags and abbreviated SHAs.

Changing repository visibility, workflow settings, or branch/ruleset settings
requires explicit maintainer authorization. A release-readiness review may
recommend that change but may not perform it. Immediately after an authorized
public conversion, verify the repository through the API, observe the pinned
public CI workflow, and establish an active `main` ruleset with no bypass actors,
required pull requests, required CI checks, and blocked force-push/deletion.

## Consequences

Private-repository runs remain conservative: one final pull-request run, the
automatic merged-`main` run, and the tag-triggered Release run are sufficient
for a patch. Redundant manual dispatches are avoided.

Standard GitHub-hosted runners are currently free for public repositories, but
the lean workflow still reduces noise and duplicated setup. Hosted macOS does
not become automatic merely because visibility changes.

The v0.2.12 release can prove code, documentation, artifacts, workflow pins, and
current settings while the repository remains private, but it may be tagged
only after the reachable-history migration in
[ADR 0034](0034-rewrite-reachable-pre-public-history-once.md). Ruleset
activation and post-conversion public CI remain explicit completion checks for
the later visibility operation; neither may be reported as complete beforehand.
