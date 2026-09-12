# agent-statusline handoff

This is the tracked, public-safe current-state record. Machine-local operational
notes may add detail, but they do not override this file, [AGENTS.md](AGENTS.md),
the roadmap, or accepted ADRs.

## Current release boundary

- Current release target: 0.3.3, build-once release artifact promotion.
- Preceding release: v0.3.2, the immutable base for this slice.
- Branch owner: Codex; only the owner changes the release branch.
- Reviewer role: one independent read-only reviewer, assigned after the exact
  candidate SHA is frozen. No second reviewer or delegated worker runs beside it.
- Both hosted workflows are active. Every pull request and `main` push runs one
  complete-ancestry audit. Documentation-only refs skip both hosted test lanes;
  full-scope refs run the Linux Python matrix and representative macOS evidence.
  One stable aggregate job reports whether all required work passed or was
  deliberately skipped. Missing, malformed, failed, cancelled, or inconsistent
  results fail closed; only reviewed canonical direct keys are accepted.
- The repository is public. Active no-bypass ruleset `22966865` protects
  `main`: pull requests and resolved review threads are required, the aggregate
  GitHub Actions result must pass against current `main`, and deletion and
  force-push are blocked.
- Runtime dependencies remain empty and versions remain Git-tag-derived.

The v0.3.3 slice locks the hosted release toolchain, builds and validates one
exact pair in a read-only job, and promotes only that named and hash-bound pair
through a dependent GitHub-Release job with repository write permission. It
changes no runtime source, runtime dependency, display, live configuration,
hosted environment, package index, or package-name installation claim.

## Stable product boundary

The Claude Code renderer retains ten rows in this order:

`PROJECT`, `MODEL`, `CONTEXT`, `USAGE`, `COST`, `SYSTEM`, `TOOLS`, `CACHE`,
`TOKENS`, `TIMING`.

Their current fields and priority order remain approved. Runtime behavior stays
local, state stays outside the repository, runtime dependencies stay empty, and
currency-labelled values remain exactly accountable. Codex remains a separate
widget-based host; [PORTING.md](docs/PORTING.md) records the verified boundary.

## Release train

Released slices through v0.2.14 cover ownership-safe installation, the locked
quality gate, malformed-input resilience, private serialized state, exact
rolling-cost attribution, session-scoped process evidence, and bounded
observation state, tracked governance, deterministic rendering safety, and
hermetic installed-renderer evidence, isolated self-test, and safe diagnostics.
They also cover pinned lean workflows, the ordinary reachable-history rewrite,
accepted historical pull-ref boundary, prospective ancestry protection,
oversized-evidence closure, protected public conversion, and exact aggregate CI.

v0.2.14 completed public-CI alignment after conversion. v0.3.0 completed the
production-ready records-and-metadata milestone promised by ADR 0030. v0.3.1
completed measured hot-path import reduction and source-hermetic benchmark
evidence. v0.3.2 completed public package metadata, portable package-page
rendering, and package-manager guidance.

The complete sequence and exclusions are authoritative in
[ROADMAP.md](docs/ROADMAP.md). Do not merge the historical hardening branch as
a whole or import a later slice into the current release.

## Resume point

v0.3.2 is complete at tagged merge
`9f7ef6b090a65c309717f1d95cd30b1f08faae85`. Exact-SHA review, protected PR and
merged-main Linux/macOS CI, tag-triggered Release, current package-description
validation, downloaded asset verification, and an isolated Python 3.9 wheel
self-test passed. Live Claude Code remains intentionally on exact installed
v0.3.1 through one status-line command and four managed hooks, with unrelated
settings and state preserved and no checkout symlink.

The v0.3.3 owner branch starts from exact v0.3.2. Change only the locked release
tooling, workflow, policy tests, one ADR, and synchronized release records
described by ADR 0042. The workflow must build once under read-only permission
and allow its dependent write job to publish only the downloaded exact pair.
TestPyPI is v0.3.4; production PyPI is v0.3.5; explicit host acquisition and
Codex evidence move to the next minor track. Runtime behavior, live
installation, accounts, environments, OIDC, package-index publication,
accepted pull refs, unreachable objects, and recovery cleanup remain separate.
[PUBLIC_READINESS.md](docs/PUBLIC_READINESS.md) records the protected baseline.

Durable decisions live in [ADRs](docs/adrs/README.md), completed behavior in the
[changelog](docs/CHANGELOG.md), review evidence in
[CODE_REVIEW.md](docs/CODE_REVIEW.md), and measured or open questions in
[RESEARCH.md](docs/RESEARCH.md).
