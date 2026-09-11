# agent-statusline handoff

This is the tracked, public-safe current-state record. Machine-local operational
notes may add detail, but they do not override this file, [AGENTS.md](AGENTS.md),
the roadmap, or accepted ADRs.

## Current release boundary

- Current release target: 0.2.11, isolated self-test and safe diagnostics.
- Preceding release: v0.2.10, the immutable base for this slice.
- Branch owner: Codex; only the owner changes the release branch.
- Reviewer role: one independent read-only reviewer, assigned after the exact
  candidate SHA is frozen. No second reviewer or delegated worker runs beside it.
- Both hosted workflows are active. Ordinary CI is Linux-only, hosted macOS is
  opt-in, and redundant runs are not dispatched while the repository is private.
- Runtime dependencies remain empty and versions remain Git-tag-derived.

The v0.2.11 release adds an installed self-test that renders the v0.2.10
synthetic contract inside fresh private home/state/config/cwd boundaries, plus a
private allowlisted breadcrumb for unexpected renderer failures. It changes no
display contract, dependency, live configuration, or repository visibility.

## Stable product boundary

The Claude Code renderer retains ten rows in this order:

`PROJECT`, `MODEL`, `CONTEXT`, `USAGE`, `COST`, `SYSTEM`, `TOOLS`, `CACHE`,
`TOKENS`, `TIMING`.

Their current fields and priority order remain approved. Runtime behavior stays
local, state stays outside the repository, runtime dependencies stay empty, and
currency-labelled values remain exactly accountable. Codex remains a separate
widget-based host; [PORTING.md](docs/PORTING.md) records the verified boundary.

## Release train

Released slices through v0.2.10 cover ownership-safe installation, the locked
quality gate, malformed-input resilience, private serialized state, exact
rolling-cost attribution, session-scoped process evidence, and bounded
observation state, tracked governance, deterministic rendering safety, and
hermetic installed-renderer evidence.

Later v0.2.x slices remain independently reviewable and releasable:

- v0.2.12: documentation, immutable workflow pins, and public-readiness closure.

The complete sequence and exclusions are authoritative in
[ROADMAP.md](docs/ROADMAP.md). Do not merge the historical hardening branch as
a whole or import a later slice into the current release.

## Resume point

Run the release-equivalent gate in [AGENTS.md](AGENTS.md), freeze one candidate
SHA, obtain one independent review of that exact SHA, and apply any correction
only as the owner. A corrected SHA must be reviewed again. After acceptance,
use the normal pull-request, automatic `main` CI, immutable annotated tag, and
release-artifact verification sequence without redundant hosted dispatches.

Durable decisions live in [ADRs](docs/adrs/README.md), completed behavior in the
[changelog](docs/CHANGELOG.md), review evidence in
[CODE_REVIEW.md](docs/CODE_REVIEW.md), and measured or open questions in
[RESEARCH.md](docs/RESEARCH.md).
