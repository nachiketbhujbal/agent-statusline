# ADR 0038: Run public CI on Linux and macOS

- Status: Accepted
- Date: 2026-09-12
- Supersedes the hosted-CI scheduling decision in [ADR 0033](0033-pin-lean-ci-and-separate-public-conversion.md)

## Context

The repository is public and protected by one stable aggregate required result.
ADR 0033 deliberately kept hosted macOS behind manual dispatch after public
conversion because changing visibility and changing CI policy were separate
operational decisions.

That separation is now complete. GitHub documents standard GitHub-hosted runner
usage as free for public repositories; larger runners remain billable
([GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)).
The product supports macOS and Linux, and its memory probe uses macOS-specific
commands. Leaving the only representative macOS lane manual would therefore
leave ordinary full-scope changes without automatic evidence on a supported
platform.

## Decision

Keep the consolidated public workflow and do not create an operating-system by
Python-version cross-product:

- one Ubuntu job retains policy, lint, build, artifact, and both installation
  shapes;
- Ubuntu retains the complete Python 3.9 through 3.13 matrix;
- one macOS job on Python 3.12 runs the complete tests and exercises the native
  memory probe for every full-scope pull request, `main` push, and manual run;
- documentation-only refs continue to run only the complete-ancestry check; and
- tag-triggered Release stays Linux-only because the wheel is platform-neutral
  and platform evidence belongs to the preceding CI runs.

The stable `required` job waits for policy, Linux, and macOS. Exact full scope
requires both test lanes to succeed; exact documentation-only scope requires
both to be skipped. Missing, malformed, failed, cancelled, or inconsistent
results fail closed. The strict canonical-key protections from
[ADR 0037](0037-require-one-aggregate-public-ci-result.md) remain in force.

Do not manually dispatch a duplicate run when the automatic pull-request or
`main` run already proves the same SHA.

## Consequences

Every full change now receives representative evidence on both supported
operating systems while preserving full Python-version coverage without a large
matrix. Documentation-only changes stay lean, and branch protection keeps one
stable required context.

If repository visibility or GitHub's runner policy changes, reevaluate this
decision before continuing automatic macOS use. PyPI publication is unrelated
and remains a separate future decision.
