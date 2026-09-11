# agent-statusline handoff

This is the tracked, public-safe current-state record. Machine-local operational
notes may add detail, but they do not override this file, [AGENTS.md](AGENTS.md),
the roadmap, or accepted ADRs.

## Current release boundary

- Current release target: 0.2.12, public-readiness closure.
- Preceding release: v0.2.11, the immutable base for this slice.
- Branch owner: Codex; only the owner changes the release branch.
- Reviewer role: one independent read-only reviewer, assigned after the exact
  candidate SHA is frozen. No second reviewer or delegated worker runs beside it.
- Both hosted workflows are active. Ordinary CI is Linux-only, hosted macOS is
  opt-in, and redundant runs are not dispatched while the repository is private.
- Runtime dependencies remain empty and versions remain Git-tag-derived.

The v0.2.12 release aligns public documentation with the released source, pins
third-party workflow actions to reviewed immutable commits, restores every root
private-workspace ignore, removes private billing detail from tracked records,
prevents another personal release identity, and stages the recoverable
reachable-history rewrite required before its tag. It changes no renderer,
display contract, runtime dependency, live configuration, or repository
visibility.

## Stable product boundary

The Claude Code renderer retains ten rows in this order:

`PROJECT`, `MODEL`, `CONTEXT`, `USAGE`, `COST`, `SYSTEM`, `TOOLS`, `CACHE`,
`TOKENS`, `TIMING`.

Their current fields and priority order remain approved. Runtime behavior stays
local, state stays outside the repository, runtime dependencies stay empty, and
currency-labelled values remain exactly accountable. Codex remains a separate
widget-based host; [PORTING.md](docs/PORTING.md) records the verified boundary.

## Release train

Released slices through v0.2.11 cover ownership-safe installation, the locked
quality gate, malformed-input resilience, private serialized state, exact
rolling-cost attribution, session-scoped process evidence, and bounded
observation state, tracked governance, deterministic rendering safety, and
hermetic installed-renderer evidence, isolated self-test, and safe diagnostics.

v0.2.12 is the final patch-train slice. The later v0.3.0 milestone remains a
separate boundary after an explicitly authorized public conversion and verified
repository protections.

The complete sequence and exclusions are authoritative in
[ROADMAP.md](docs/ROADMAP.md). Do not merge the historical hardening branch as
a whole or import a later slice into the current release.

## Resume point

Run the release-equivalent gate in [AGENTS.md](AGENTS.md), freeze one prevention
candidate SHA, and obtain one independent review of that exact SHA. Do not tag
or release it: the reachable-history audit is expected to fail until the later
ADR 0034 rewrite. Preserve a verified offline bundle and stop for maintainer
approval before any workflow disablement, protection change, force-with-lease
ref update, tag movement, or release repair. The rewritten candidate requires a
renewed exact-SHA review before the normal private v0.2.12 release sequence.
Do not change visibility; [PUBLIC_READINESS.md](docs/PUBLIC_READINESS.md) defines
the rewrite, conversion, and post-conversion verification boundaries.

Durable decisions live in [ADRs](docs/adrs/README.md), completed behavior in the
[changelog](docs/CHANGELOG.md), review evidence in
[CODE_REVIEW.md](docs/CODE_REVIEW.md), and measured or open questions in
[RESEARCH.md](docs/RESEARCH.md).
