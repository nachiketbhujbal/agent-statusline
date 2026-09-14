# agent-statusline handoff

This is the tracked, public-safe current-state record. Machine-local operational
notes may add detail, but they do not override this file, [AGENTS.md](AGENTS.md),
the roadmap, or accepted ADRs.

## Current release boundary

- Current release target: 0.3.6, separate trusted package-index promotion workflows.
- Preceding release: v0.3.5, now published on GitHub, TestPyPI, and PyPI.
- Current operational target: cut v0.3.6 from the completed workflow support on
  `main`, publish its exact GitHub Release pair through TestPyPI and PyPI, then
  upgrade the local installed command from production PyPI.
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

v0.3.5 is tagged and released with the approved concise README and one exact
artifact pair on GitHub, TestPyPI, and production PyPI. TestPyPI and PyPI are
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
completed the public landing page and preserved exact production-ready package
artifacts.

The complete sequence and exclusions are authoritative in
[ROADMAP.md](docs/ROADMAP.md). Do not merge the historical hardening branch as
a whole or import a later slice into the current release.

## Resume point

v0.3.5 is complete at tagged merge
`87f1e31b71d00182af8530e17cca62e005c6b001`. Exact-SHA review, protected PR and
merged-main CI, tag-triggered build-once GitHub Release, manually approved OIDC
TestPyPI publication, public hash verification, and an isolated Python 3.9
wheel self-test passed. The exact published pair is
`agent_statusline-0.3.5-py3-none-any.whl` at
`e4a681a93a7f840db024489da109bb264b98e09fa6e05d40772d3beeacc47cb0` and
`agent_statusline-0.3.5.tar.gz` at
`ed77b89ba1d417b995beca5644c284f8e6d25aca9d793dd4266a841c0dc1da24`.

The paired promotion implementation merged through PR #24 as
`8030d4353ec71418eb42644275c6e68ad3877d3f`; PR #25 then recorded the durable
proportionate-engineering default at the following `main` boundary,
`d438ed3dd08459c69792433e288686942d729ed4`. Production v0.3.5 promotion run
34797988834 passed exact hash verification and isolated installation, and the
TestPyPI publisher migration is complete.

Finish v0.3.6 by aligning these current records, running the required local
gate and one exact-SHA review, merging through protected `main`, and tagging
the verified merge. Let `release.yml` create the GitHub Release, then manually
publish that exact pair through `publish-testpypi.yml` followed by
`publish-pypi.yml`. After production verification, upgrade the local uv-managed
tool from `agent-statusline==0.3.6`, confirm its version and existing Claude
Code command path, and do not read or alter live accounting state. Explicit
host acquisition and Codex evidence remain on the next minor track. Runtime
behavior, accepted pull refs, unreachable objects, and recovery cleanup remain
separate.
[PUBLIC_READINESS.md](docs/PUBLIC_READINESS.md) records the protected baseline.

Durable decisions live in [ADRs](docs/adrs/README.md), completed behavior in the
[changelog](docs/CHANGELOG.md), review evidence in
[CODE_REVIEW.md](docs/CODE_REVIEW.md), and measured or open questions in
[RESEARCH.md](docs/RESEARCH.md).
