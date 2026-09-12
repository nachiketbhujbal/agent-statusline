# agent-statusline handoff

This is the tracked, public-safe current-state record. Machine-local operational
notes may add detail, but they do not override this file, [AGENTS.md](AGENTS.md),
the roadmap, or accepted ADRs.

## Current release boundary

- Current release target: 0.3.0, the production-ready supported milestone.
- Preceding release: v0.2.14, the immutable base for this slice.
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

The v0.3.0 slice names the already-proven patch train as the supported public
baseline. It updates only version-boundary records, immutable-tag installation
guidance, and package maturity metadata. It changes no renderer, display
contract, runtime dependency, state, installer, workflow, or live wiring.

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

v0.2.14 completed the public-CI and installation-documentation alignment after
public conversion. v0.3.0 is the records-and-metadata milestone promised by
ADR 0030, not another hardening integration branch.

The complete sequence and exclusions are authoritative in
[ROADMAP.md](docs/ROADMAP.md). Do not merge the historical hardening branch as
a whole or import a later slice into the current release.

## Resume point

v0.2.14 is complete at tagged merge
`0b47d8f5fccd3417bbad5f4d695dbff2d910e3e1`. Exact-SHA review, PR and merged-main
Linux/macOS CI, tag-triggered Release, downloaded asset verification, and an
isolated Python 3.9 wheel self-test passed. Claude Code remains on exact
installed v0.2.13 because v0.2.14 changed only CI, policy tests, and
documentation; its four managed hooks and unrelated live state remain intact.

The v0.3.0 owner branch starts from exact v0.2.14. The historical
`codex/hardening/v0.3.0-production-readiness` branch is superseded source
material and must not be merged or cherry-picked wholesale. Reconcile it only
to prove that the sequential patch releases cover its intended hardening. The
candidate may change the tracked milestone records, README release tag, ADR
0039, and package maturity classifier; no runtime source changes are in scope.
Orphan cleanup, accepted pull-ref changes, PyPI publication, live installation
changes, performance work, and host-architecture work remain separate.
[PUBLIC_READINESS.md](docs/PUBLIC_READINESS.md) records the protected baseline.

Durable decisions live in [ADRs](docs/adrs/README.md), completed behavior in the
[changelog](docs/CHANGELOG.md), review evidence in
[CODE_REVIEW.md](docs/CODE_REVIEW.md), and measured or open questions in
[RESEARCH.md](docs/RESEARCH.md).
