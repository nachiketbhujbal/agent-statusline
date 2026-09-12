# agent-statusline handoff

This is the tracked, public-safe current-state record. Machine-local operational
notes may add detail, but they do not override this file, [AGENTS.md](AGENTS.md),
the roadmap, or accepted ADRs.

## Current release boundary

- Current release target: 0.2.13, oversized-audit and hosted-exposure closure.
- Preceding release: v0.2.12, the immutable base for this slice.
- Branch owner: Codex; only the owner changes the release branch.
- Reviewer role: one independent read-only reviewer, assigned after the exact
  candidate SHA is frozen. No second reviewer or delegated worker runs beside it.
- Both hosted workflows are active. Every pull request and `main` push runs one
  complete-ancestry audit; documentation-only refs skip the full Linux gate,
  hosted macOS remains opt-in, and one stable aggregate job reports whether all
  required work passed or was deliberately skipped. Missing or malformed scope
  fails closed; the exact unconditional job condition and self-contained
  fail-fast script are enforced, and only their reviewed canonical direct keys
  are accepted; quoted, escaped, whitespace-varied, duplicate, or unexpected
  keys fail closed.
- The repository is public. Active no-bypass ruleset `22966865` protects
  `main`: pull requests and resolved review threads are required, the aggregate
  GitHub Actions result must pass against current `main`, and deletion and
  force-push are blocked.
- Runtime dependencies remain empty and versions remain Git-tag-derived.

The v0.2.13 correction fails closed on distribution members and reachable blobs
above the bounded privacy-audit size, records the complete retained Actions
exposure inventory and authorized artifact cleanup, and establishes the
protected public baseline. It changes no renderer, display contract, runtime
dependency, Git history, release tag or asset, or live configuration.

## Stable product boundary

The Claude Code renderer retains ten rows in this order:

`PROJECT`, `MODEL`, `CONTEXT`, `USAGE`, `COST`, `SYSTEM`, `TOOLS`, `CACHE`,
`TOKENS`, `TIMING`.

Their current fields and priority order remain approved. Runtime behavior stays
local, state stays outside the repository, runtime dependencies stay empty, and
currency-labelled values remain exactly accountable. Codex remains a separate
widget-based host; [PORTING.md](docs/PORTING.md) records the verified boundary.

## Release train

Released slices through v0.2.12 cover ownership-safe installation, the locked
quality gate, malformed-input resilience, private serialized state, exact
rolling-cost attribution, session-scoped process evidence, and bounded
observation state, tracked governance, deterministic rendering safety, and
hermetic installed-renderer evidence, isolated self-test, and safe diagnostics.
They also cover pinned lean workflows, the ordinary reachable-history rewrite,
accepted historical pull-ref boundary, and prospective ancestry protection.

v0.2.13 is the narrow correction required after the final v0.2.12 audit exposed
an oversized-evidence bypass and retained unsafe Actions artifacts. Its public
conversion and verified `main` ruleset satisfy the infrastructure prerequisite
for the later v0.3.0 milestone without starting that milestone.

The complete sequence and exclusions are authoritative in
[ROADMAP.md](docs/ROADMAP.md). Do not merge the historical hardening branch as
a whole or import a later slice into the current release.

## Resume point

The v0.2.12 release, ADR 0034 ordinary-ref rewrite, historical Release repair,
and retained Actions inventory are complete. Sixteen unsafe Actions artifacts
were deleted with explicit authorization; at the recorded post-deletion
snapshot, all 41 then-retained logs and all ten remaining artifacts passed a
complete second scan. Twelve GitHub-managed historical pull heads remain as the
explicitly accepted ADR 0035 residue.

The protected public baseline is complete through active ruleset `22966865` and
its stable required CI result. v0.2.13 remains untagged and unreleased. Any tag,
GitHub Release, live upgrade, orphan cleanup, accepted pull-ref change, or v0.3.0
work requires a separate authorized objective. [PUBLIC_READINESS.md](docs/PUBLIC_READINESS.md)
records the exact completed boundary.

Durable decisions live in [ADRs](docs/adrs/README.md), completed behavior in the
[changelog](docs/CHANGELOG.md), review evidence in
[CODE_REVIEW.md](docs/CODE_REVIEW.md), and measured or open questions in
[RESEARCH.md](docs/RESEARCH.md).
