# agent-statusline handoff

This is the tracked, public-safe current-state record. Machine-local operational
notes may add detail, but they do not override this file, [AGENTS.md](AGENTS.md),
the roadmap, or accepted ADRs.

## Current release boundary

- Current release target: 0.4.4, native Linux and WSL memory pressure.
- Preceding release: v0.4.3, configurable context guard and Stop timing.
- Branch owner: Codex on `codex/feat/v0.4.4-linux-memory`.
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

v0.4.3 is tagged and released with one exact artifact pair on GitHub, TestPyPI,
and production PyPI. v0.4.4 changes only the native memory probe, its tests,
CI assertion, and synchronized public records; it does not alter the approved
display, accounting, installer, or dependencies. TestPyPI and PyPI are
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
v0.4.0 completed the explicit host-acquisition architecture boundary. v0.4.1
completed the normalized Claude acquisition adapter without changing display.
v0.4.2 completed the documented local per-session metrics contract. v0.4.3
completed configurable context warnings and user-visible Stop timing. v0.4.4
is implementing native Linux and WSL memory pressure parity.

The complete sequence and exclusions are authoritative in
[ROADMAP.md](docs/ROADMAP.md). Do not merge the historical hardening branch as
a whole or import a later slice into the current release.

## Resume point

Authorized v0.4.4 work starts from clean released `main`
`706d36891709fbb1b1df98f046ca45fec8cbb33d` on
`codex/feat/v0.4.4-linux-memory`. The bounded requirement is to preserve the
macOS `sysctl` / `vm_stat` probe and use Linux `/proc/meminfo` values
`MemTotal - MemAvailable`, with WSL intentionally reporting its Linux-visible
capacity. The normalized renderer fields and ten-row display stay unchanged;
compressed memory remains macOS-only. Required evidence is synthetic valid,
missing, and malformed Linux coverage, retained macOS coverage, direct native
Linux/macOS CI assertions, the complete locked local gate, one independent
exact-SHA review, protected PR/main CI, annotated v0.4.4 GitHub Release,
TestPyPI and PyPI promotion, and clean production-index installation proof.
No GitHub issue currently tracks this maintainer-requested slice.

If interrupted, inspect the branch status and most recent commit, complete any
remaining gate, then update this paragraph with exact SHA and evidence before
requesting independent review. Any correction after review requires a renewed
review of the new exact SHA. Do not tag until the reviewed candidate is merged
and exact merged `main` CI passes.

v0.4.3 is complete at tagged merge
`dc7000b4c2bbb5b659b8837cee28b9055b95787e`. Exact candidate
`e4a0d91762fbb1bc08bb891c07766bec0ea86cec` passed independent no-findings
review and the complete local gate. PR #35 closed issues 31 and 32; PR CI run
35009998711 and merged-main CI run 35010141037 passed before annotated tag
object `c1d894e5f0b24f3f82c960873df0c9d7fe056292` and GitHub Release run
35010394642. TestPyPI run 35010556768 and production PyPI run 35011232785
published and clean-install verified the same exact wheel at
`adda5eccc1e82279a37608c9aeec06518b9596aef68700009b21ee18fe9d00ae`
and source archive at
`bf8637bc0e0ca2877869194e9f5487468bd9e49fe23788604d77631716836b7b`.
TestPyPI's first clean-install attempt reached its Simple Index before v0.4.3
appeared there, after its JSON hashes had already matched; the failed-job rerun
passed after propagation. Production PyPI passed on its first verification.

v0.4.2 is complete at tagged merge
`5dcbb5792bb718925a02ca4e9ee6952126184157`. Exact candidate
`dd4b55d17faf5c7b9b86bf8283b2a1e7437ab62f` passed renewed independent review;
PR #34 closed issue 30, merged-main CI run 35006217099, GitHub Release run
35006440871, TestPyPI run 35006652209, and production PyPI run 35008034856
passed. The production clean-install check initially reached the Simple Index
before it exposed the already hash-verified files; its rerun passed after
propagation. GitHub, TestPyPI, and PyPI expose the same exact wheel at
`a1696f885a880bd15b9c8b2bcad9c51c5ecac33b7b08a02e29b3fd2df94decad`
and source archive at
`669124024f6fd3c8f27830395ee9e49a5274cb86330e3d0b5828206be3bbefd1`.

v0.4.1 is complete at tagged merge
`d7b8341ed9cfea801f8f8d50c9832ead10e7548e`. Exact candidate
`3193300a70dfc9d8f892cc330d694126c84e37af` passed independent review; PR #33,
merged-main CI run 35000480030, GitHub Release run 35000669543, TestPyPI run
35000820947, and production PyPI run 35001447162 passed. GitHub, TestPyPI, and
PyPI expose the same exact wheel at
`ffe0f61c134158bc6894590ecc47c1f7509f37bebcf7ae20b31ddd4b5af9266c`
and source archive at
`173a95ee032e03f011d0b3638e1bc0945b8fbbce0a28686be5e43ca0c97ad45f`.

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
exact token/session facts but no exact cost field. ADR 0047 preserves that
architecture while updating the follow-on order: v0.4.2 published local
per-session metrics for issue 30, and v0.4.3 completed the configurable
context guard and Stop timing from issues 31 and 32. The synthetic-fixture
Codex parser and any opt-in Codex collector/query surface follow that local
integration sequence.

Exact architecture candidate
`d8ceb7bb5537b745df070214aafd68c866f226ea` passed the complete local gate and
one independent no-findings review. PR #28 passed the documentation-only hosted
gate and merged it as `5fe305a6643b8141dd1874662730b1f020dea32d`;
automatic main run 34873106649 passed the same lean required lane.

The v0.4.1 adapter does not add a Codex implementation, configuration mutation,
renderer claim, or Codex currency accounting. Accepted pull refs, unreachable
objects, and recovery cleanup remain separate.
[PUBLIC_READINESS.md](docs/PUBLIC_READINESS.md) records the protected baseline.

Durable decisions live in [ADRs](docs/adrs/README.md), completed behavior in the
[changelog](docs/CHANGELOG.md), review evidence in
[CODE_REVIEW.md](docs/CODE_REVIEW.md), and measured or open questions in
[RESEARCH.md](docs/RESEARCH.md).
