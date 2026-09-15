# agent-statusline handoff

This is the tracked, public-safe current-state record. Machine-local operational
notes may add detail, but they do not override this file, [AGENTS.md](AGENTS.md),
the roadmap, or accepted ADRs.

## Current release boundary

- Current release target: 0.4.1, normalized Claude acquisition facts.
- Preceding release: v0.4.0, explicit host-acquisition architecture.
- Branch owner: Codex on `codex/feat/v0.4.1-normalized-acquisition`.
- Reviewer role: none active.
- Hosted CI, Release, and paired package-index promotion workflows are active.
  Every pull request and `main` push runs one
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

v0.4.0 is tagged and released with one exact artifact pair on GitHub, TestPyPI,
and production PyPI. TestPyPI and PyPI are
bound respectively to `publish-testpypi.yml` and `publish-pypi.yml`; both
GitHub environments require maintainer approval, accept only branch `main`,
and allow no bypass. No package-index token or secret is stored.

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
rendering, and package-manager guidance. v0.3.3 completed locked build-once
artifact promotion and exact GitHub Release publication. v0.3.4 completed
trusted TestPyPI publication and exact public-index verification. v0.3.5
completed the public landing page and first production PyPI publication.
v0.3.6 completed separate, reusable TestPyPI and PyPI promotion workflows.
v0.4.0 completed the explicit host-acquisition architecture boundary.

The complete sequence and exclusions are authoritative in
[ROADMAP.md](docs/ROADMAP.md). Do not merge the historical hardening branch as
a whole or import a later slice into the current release.

## Resume point

v0.4.1 is the active behavior-preserving implementation of ADR 0046. It adds
one normalized Claude acquisition adapter and routes the existing renderer
through it without changing display, accounting, installation, hooks, or
state. The exact candidate still requires the complete local gate and one
independent review before publication.

v0.4.0 is complete at tagged merge
`125f60527d44cc3dcf20ff8c384542944dacbf8d`. GitHub Release run 34997267833,
TestPyPI run 34997383308, and production PyPI run 34997703359 published and
verified the same exact artifact pair. The initial PyPI clean-install check ran
before the Simple Index exposed the already verified files; its isolated rerun
passed after propagation.

v0.3.6 is complete at tagged merge
`9a92560be103a56e542a27ce2aee423c4255f9e0`. Exact candidate
`ca4a0af180d24e8e9f5462771447ad97adb5f32f` passed the complete local gate and
one independent review. PR #26, merged-main CI, annotated tag object
`598b3667dec7c2c1bba984b7ce69600fddc63623`, GitHub Release run 34801071659,
TestPyPI run 34801160225, and production PyPI run 34801290059 passed.

GitHub, TestPyPI, and PyPI report the same exact published pair:
`agent_statusline-0.3.6-py3-none-any.whl` at
`786f74d79311b2c6c7dbdc9cde460156426941beb85a977a823c0b6fcbbe20ff` and
`agent_statusline-0.3.6.tar.gz` at
`d4802e833701b30c06b22b31dc2ca73fff49d991d69649302b7c0902e4b4fe55`.
The local uv-managed command was upgraded from production PyPI and reports
0.3.6; Claude Code's managed command and complete settings bytes were unchanged,
and an isolated self-test passed without reading live accounting state.

The v0.4.0 research boundary is now measured and recorded in ADR 0046. Installed
Codex still exposes a built-in-widget footer rather than an arbitrary command;
stable hooks provide a credible acquisition trigger, and local rollouts expose
exact token/session facts but no exact cost field. The proposed follow-on train
is 0.4.1 normalized acquisition facts, 0.4.2 a synthetic-fixture Codex parser,
and only then consideration of an opt-in 0.4.3 collector/query surface.

Exact architecture candidate
`d8ceb7bb5537b745df070214aafd68c866f226ea` passed the complete local gate and
one independent no-findings review. PR #28 passed the documentation-only hosted
gate and merged it as `5fe305a6643b8141dd1874662730b1f020dea32d`;
automatic main run 34873106649 passed the same lean required lane.

No implementation, Codex configuration mutation, renderer claim, or Codex
currency accounting is authorized yet. Runtime behavior, accepted pull refs,
unreachable objects, and recovery cleanup remain separate.
[PUBLIC_READINESS.md](docs/PUBLIC_READINESS.md) records the protected baseline.

Durable decisions live in [ADRs](docs/adrs/README.md), completed behavior in the
[changelog](docs/CHANGELOG.md), review evidence in
[CODE_REVIEW.md](docs/CODE_REVIEW.md), and measured or open questions in
[RESEARCH.md](docs/RESEARCH.md).
