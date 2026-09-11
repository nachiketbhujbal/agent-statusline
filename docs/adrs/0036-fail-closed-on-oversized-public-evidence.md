# ADR 0036: Fail closed on oversized public evidence

- Status: Accepted
- Date: 2026-09-11
- Extends [ADR 0033](0033-pin-lean-ci-and-separate-public-conversion.md)

## Context

The v0.2.12 artifact and reachable-history privacy scanners inspected textual
evidence only up to two MiB. A larger archive member or reachable blob was
silently skipped, so synthetic private billing evidence immediately beyond the
limit passed both checks. The released repository contains no reachable object
above that boundary, but the policy itself did not fail closed.

## Decision

Reject every regular distribution member and reachable Git blob larger than
the two-MiB audit boundary. Do not attempt to infer that an unscanned object is
safe from its name, encoding, or apparent binary shape. Keep the bounded scan
for smaller objects and preserve the existing private-path, billing-evidence,
personal-provider-email, and identity checks.

The package is a small dependency-free tool and has no legitimate large binary
payload. Any future need for a larger tracked or distributed object requires a
separate reviewed policy change with a bounded streaming inspection design.

## Consequences

An oversized object now blocks local review, pull-request ancestry, `main` CI,
and Release before publication. Synthetic regressions prove that both scanners
reject the exact size boundary previously skipped. Existing ordinary history
requires a renewed strict scan but no rewrite when it contains no oversized
blob.
