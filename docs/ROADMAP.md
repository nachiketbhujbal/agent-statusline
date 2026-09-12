# Roadmap

Release-scoped work belongs here. Ideas without a committed release stay in
[DEFERRED.md](DEFERRED.md).

## Release sequence

The hardening work is shipped as sequential, single-purpose 0.2.x patches rather
than one large release ([ADR 0030](adrs/0030-ship-hardening-as-small-pre-one-patches.md)).
Each release is cut from the preceding released state, carries only its own
implementation, tests, ADR and documentation, and is proven by its own gate and
installed-artifact evidence.

| Release | Primary purpose | Status |
| --- | --- | --- |
| 0.2.1 | Ownership-safe installation and removal | **Released** |
| 0.2.2 | Locked local quality gate | **Released** |
| 0.2.3 | Malformed host-input resilience | **Released** |
| 0.2.4 | Private, serialized runtime state | **Released** |
| 0.2.5 | Exact rolling-cost attribution | **Released** |
| 0.2.6 | Session-scoped process evidence | **Released** |
| 0.2.7 | Bounded observation state | **Released** |
| 0.2.8 | Tracked governance and review records | **Released** |
| 0.2.9 | Width-safe, sanitized rendering | **Released** |
| 0.2.10 | Hermetic installed-renderer evidence | **Released** |
| 0.2.11 | Isolated self-test and safe diagnostics | **Released** |
| 0.2.12 | Documentation, pinned workflow, and public-readiness closure | **Released** |
| 0.2.13 | Oversized-audit and hosted-exposure closure | **Released** |
| 0.2.14 | Public CI and installation-documentation alignment | **Released** |
| 0.3.0 | Production-ready milestone | **Released** |
| 0.3.1 | Measured hot-path performance | **Released** |
| 0.3.2 | PyPI metadata and package-page readiness | **Current** |
| 0.3.3 | Build-once release artifact promotion | Planned |
| 0.3.4 | Trusted TestPyPI publication and verification | Planned |
| 0.3.5 | Trusted production PyPI publication and verification | Planned |
| 0.4.0 | Explicit host-acquisition architecture | Planned |

0.2.1 through 0.2.14, v0.3.0, and v0.3.1 are tagged and released. The v0.3.0 boundary
names that completed, independently proven train as the production-ready
supported public baseline. Each boundary retains its exact review and artifact
evidence; GitHub Release objects begin at v0.2.4. The historical hardening
branch remains source material and is not a merge candidate.

## 0.2.1 — ownership-safe installation

Released:

- Preserve unrelated settings, hook events, groups, matchers and their order.
- Fail closed on unreadable, malformed, non-object, or non-UTF-8 configuration
  before any mutation on both the install and uninstall paths.
- Remove only configuration whose command exactly matches what this installer
  writes; preserve a status line, hook, or checkout symlink whose ownership
  cannot be proven.
- Honour `CLAUDE_CONFIG_DIR`, including paths containing spaces.
- Publish atomically through a symlink with the resolved target's mode, confined
  to the configuration directory, backing up first and leaving no temporary file
  behind on failure.
- Keep reinstallation idempotent.

## 0.2.2 — locked local quality gate

Released:

- A committed `uv.lock`, a `uv >=0.12` requirement, and dependency-group
  development tools.
- Pre-commit hooks for repository hygiene, Ruff, Black, and mypy, run from the
  locked environment; the external `pre-commit-hooks` repository is pinned to
  an immutable commit.
- Subprocess-aware pytest coverage and build configuration.
- Only the mechanical formatting and typing corrections needed for the exact
  v0.2.1 source to pass the declared gate; no behavior change.

## 0.2.3 — malformed host-input resilience

Released:

- Require decoded payload and transcript rows to have mapping shape before
  field access; use the established fallback or skip unsupported rows.
- Validate path, sequence, permission-mode, and session-identifier shapes before
  passing them to filesystem, mapping-key, or sequence operations.
- Reject unsupported transcript conversation identifiers and tool names before
  they can poison incremental or accounting state, including cached roots from
  an earlier run.
- Normalize host-derived numbers through bounded finite integer/fractional
  helpers while preserving accepted numeric strings and exact integers.
- Protect payload, transcript, reset-time, and formatter boundaries from
  invalid, non-finite, and oversized values without emitting `nan` or `inf`.
- Keep absence distinct from zero where it carries meaning, especially payload
  cost, and preserve all ten labels, their order, and valid display output.

## 0.2.4 — private, serialized runtime state

Released:

- Route package-owned ledger, transcript, probe, payload, hook, and rate-history
  state through one dependency-free storage service.
- Serialize each file's complete read-modify-write transaction with a private
  sidecar lock; append rate-history records under the same lock.
- Publish replacement files through unique private same-directory temporaries,
  preserving prior bytes and cleaning up the attempted temporary on ordinary
  failure.
- Refuse final symlink and non-regular state or lock entries, keep direct state
  names inside the once-resolved root, and apply `0700` to roots the package
  creates and `0600` to package-owned state and lock files.
- Defer state-root initialization until first filesystem use, and keep
  stateless rendering available when optional state cannot be read or published
  without weakening refusal or prior-byte preservation.
- Normalize malformed nested package caches while preserving valid siblings,
  monotonic transcript progress, coupled transcript offset/totals validity,
  probe fallback behavior, and exact computed ledger aggregates.
- Preserve all ten rows, valid output, and the existing accounting model. This
  release adds no v0.2.5 cost-event or attribution semantics.

## 0.2.5 — exact rolling-cost attribution

Released:

- Journal finite positive lifetime-cost deltas with observation and assistant
  timestamps inside the existing locked ledger transaction.
- Migrate existing lifetimes as idempotent non-accrual seeds without inventing
  historical spend timing.
- Compute `24h`, `7d`, and `30d` independently with inclusive boundaries and an
  exact `≥` lower-bound marker whenever relevant evidence is unattributable or
  invalid.
- Prefer newest assistant time, fall back to observation time, and clamp future
  evidence so a bad clock cannot keep spend inside every window.
- Retain 35 days of valid evidence without pruning malformed rows merely to
  manufacture completeness.
- Preserve lifetime session, resume/base/run, `last5`, `all`, row order, all
  non-cost fields, private storage, and the zero-runtime-dependency boundary.

## 0.2.6 — session-scoped process evidence

Released:

- Cache the combined process snapshot under the host's opaque string session
  identifier, with a separately namespaced parent-PID fallback.
- Prevent concurrent sessions from borrowing each other's PID, process count,
  or resident-memory evidence during the cache TTL.
- Preserve one internally consistent snapshot for both per-session and
  machine-wide totals without adding a second cold-render subprocess.
- Keep the existing eight-second TTL; retention and entry-count limits remain
  the v0.2.7 boundary.

## 0.2.7 — bounded observation state

Released:

- Expire probe rows older than seven days and retain at most 256, always
  preserving the active observation while evicting the oldest remaining rows.
- Expire transcript rows older than 35 days and retain at most 512, always
  preserving the active transcript and its coupled offset/totals evidence.
- Touch an unchanged active transcript row no more than hourly; stamp legacy
  rows once so they acquire a real retirement boundary.
- Compact rate-limit history at one MiB under the existing lock and atomic
  publication path, retaining the newest valid whole-record suffix and
  discarding malformed rows during compaction.
- Keep unchanged below-bound rate observations tail-only and preserve private
  modes, final-entry refusal, failure cleanup, output, and accounting behavior.

## 0.2.8 — tracked governance and review records

Released:

- Add one authoritative tracked instruction file and one concise public-safe
  current-state handoff.
- Preserve measured research separately from release commitments, date
  environment-specific evidence, and require re-verification before promoting
  a time-sensitive external claim.
- Record exactly one branch owner and one independent reviewer per release.
  Work serially, with at most one reviewer active at a time; the owner alone
  applies corrections and every changed candidate receives renewed exact-SHA
  review ([ADR 0026](adrs/0026-coordinate-one-owner-and-one-reviewer.md)).
- Validate relative Markdown links, ADR index/file agreement and intentional
  reservations, release-version agreement, ownership wording, and public-safe
  governance text through a deterministic repository check.
- Keep v0.2.9 rendering, v0.2.10 installed evidence, v0.2.11 diagnostics,
  v0.2.12 workflow/public-readiness work, live configuration, and repository
  visibility unchanged.

## 0.2.9 — width-safe, sanitized rendering

Released:

- Measure printable terminal cells for wide, full-width, and combining Unicode.
- Sanitize labels, separators, and segments while preserving only package-owned
  SGR styling; remove line, control, format, bidirectional, and other terminal
  escape input before fitting.
- Clip only at code-point boundaries, enforce every physical line's width, and
  preserve continuation alignment under observed host whitespace trimming.
- Keep nested-Git branch discovery from rebinding the current-workspace disk
  probe.
- Floor the displayed 5h/7d allowance percentage, retain the burn-rate decimal,
  and preserve numeric `pct >= 100` overage behavior.
- Keep v0.2.10 installed evidence, v0.2.11 diagnostics, v0.2.12 workflow/public-
  readiness work, live configuration, and repository visibility unchanged.

## 0.2.10 — hermetic installed-renderer evidence

Released:

- Commit privacy-neutral payload and transcript templates with no host paths,
  identifiers, or captured live state.
- Materialize current assistant/reset clocks and disposable absolute project,
  transcript, and tool paths at runtime.
- Make source pytest and the installed-wheel smoke consume one resolved contract
  requiring exact `ORDER` and transcript-backed cache, token, tool, and timing
  evidence from an unrelated working directory.
- Isolate `HOME` and `AGENT_STATUSLINE_STATE`; build once and install the actual
  wheel without dependencies.
- Require the evidence in the source distribution and exclude it from the
  runtime wheel.
- Keep v0.2.11 diagnostics, v0.2.12 workflow/public-readiness work, runtime
  behavior, live configuration, and repository visibility unchanged.

## 0.2.11 — isolated self-test and safe diagnostics

Released:

- Add `agent-statusline selftest` using the v0.2.10 synthetic contract in a
  fresh child with isolated private home, configuration, state, and cwd.
- Derive expected labels from `ORDER`, require all ten rows, suppress child
  output, and reject public, symlinked, or non-regular private state.
- On unexpected renderer failure, atomically publish only schema, UTC time,
  fixed phase, and exception type to a private breadcrumb before preserving the
  original exception.
- Never record messages, tracebacks, payloads, transcripts, paths, commands, or
  filenames; malformed input and broken pipes create no breadcrumb.
- Keep v0.2.12 workflow/public-readiness work, live installation, performance,
  and repository visibility unchanged.

## 0.2.12 — public-readiness closure

Released:

- Align README, internals, porting guidance, release records, and handoff state
  with the source and tags shipped through v0.2.11.
- Pin every third-party action to a reviewed full commit SHA with a readable
  release comment and enforce that policy locally and in hosted workflows.
- Track `/.claude/`, `/.pvt/`, and `/.worktrees/` as permanent private
  boundaries; reject an undefined dependency-guard prefix.
- Generalize private billing evidence from ADR 0018 and supersede it with the
  public-safe lean-CI and conversion boundary in ADR 0033.
- Prevent future personal merge/tag identities and execute the recoverable,
  one-time reachable-history migration in ADR 0034 before tagging v0.2.12.
- Accept only the twelve immutable historical pull heads recorded by ADR 0035;
  audit every future pull-request, `main`, and release ancestry while retaining
  the documentation-only full-gate cost boundary.
- Record a reproducible history/ref, artifact, secret/environment, workflow, and
  repository-setting audit in [PUBLIC_READINESS.md](PUBLIC_READINESS.md).
- Release under the current private process. Present a direct visibility
  recommendation before any conversion; visibility and repository protection
  changes remain separately authorized operations.

## 0.2.13 — oversized-audit and hosted-exposure closure

Released:

- Reject every distribution member and reachable blob above the bounded
  privacy-audit size instead of silently skipping it.
- Prove the old bypass with synthetic archive and Git-history regressions, then
  rerun the strict audit over the ordinary reachable graph.
- Inventory every retained Actions log and artifact, remove only the explicitly
  authorized unsafe artifacts, and verify the remaining hosted surface.
- Align the changelog, roadmap, handoff, review ledger, and public-readiness
  verdict with released v0.2.12 and the completed inventory.
- Establish public visibility and the active no-bypass `main` ruleset, with one
  stable aggregate required CI result that fails closed on missing or malformed
  scope, requires an exact unconditional job and self-contained fail-fast script,
  and cannot be made conditional, non-blocking, or shell-overridden.
- Keep runtime behavior, Git history, release tags and assets, existing workflow
  runs and logs, live state, and the accepted ADR 0035 pull-ref residue unchanged.

## 0.2.14 — public CI and installation-documentation alignment

Released:

- Run the complete Python 3.9 through 3.13 matrix on Linux and one representative
  Python 3.12 lane on macOS for every full-scope pull request, `main` push, and
  manual run.
- Include both hosted test lanes in the stable aggregate required result; require
  both to pass for full scope and both to be skipped for documentation-only scope.
- Keep one combined Linux policy/build/install job, immutable action pins,
  ancestry auditing on every ref, and Linux-only tag publication.
- Replace current private-repository billing language with the public-runner
  decision in ADR 0038 while preserving earlier ADRs as historical records.
- Document the normal no-clone command-line installation from an immutable public
  Git tag; defer package-name installation until a separate PyPI decision.
- Keep runtime behavior, renderer output, dependencies, live installed v0.2.13,
  accepted historical refs, unreachable objects, and v0.3.0 work unchanged.

## 0.3.0 — production-ready milestone

Released:

- Declare the completed v0.2.1 through v0.2.14 train the supported public
  baseline after every patch's independent review, immutable tag, and release-
  specific artifact proof. GitHub Release objects begin at v0.2.4, when the
  hosted Release workflow was enabled.
- Mark the distribution `Production/Stable` while retaining pre-1.0 semantic-
  versioning rules; this is a product-readiness statement, not a promise that
  future 0.x minors cannot change compatibility.
- Point the normal no-clone installation and upgrade commands at the immutable
  v0.3.0 tag; an exact-tag install must be replaced explicitly rather than
  relying on `uv tool upgrade`.
- Record that the historical hardening branch is superseded source material
  whose intended work landed through corrected, individually proven patches;
  do not merge or cherry-pick it wholesale.
- Change no runtime source, renderer behavior, approved row or field,
  dependency, installer, workflow, state, or live configuration.
- Keep PyPI publication, accepted historical pull refs, unreachable-object
  cleanup, performance work, and host architecture outside this milestone.

## 0.3.1 — measured hot-path performance

Released:

- Repeat the interpreter, import-only, warm-render, and cold-render baseline
  against exact v0.3.0 before changing the hot path.
- Lazy-load `subprocess` on probe cache misses and `argparse` only for the ledger
  CLI; remove `shutil` from fresh renderer processes while preserving ordinary
  terminal-width and private atomic state publication behavior and consistently
  normalizing an unusable zero-column terminal result to the existing fallback.
- Add a deterministic import-budget regression that names the expensive modules
  excluded from the renderer import boundary.
- Add a synthetic isolated benchmark command reporting interpreter floor, warm
  and cold render medians and ranges, plus the ratio to interpreter startup.
- Track benchmark output as evidence; do not gate on elapsed time until enough
  cross-machine history exists to define a non-flaky boundary.
- Preserve every approved row and field. Performance work does not redesign the
  display, alter accounting, add dependencies, or change live configuration.

## 0.3.2 — PyPI metadata and package-page readiness

Current release:

- Align the v0.3.1 completion boundary across the changelog, roadmap, review
  ledger, and handoff.
- Add standard public Source, Issues, Changelog, Homepage, and Documentation
  package metadata.
- Make README links portable to rendering outside the repository, including a
  future package-index project page.
- Document `uv tool`, `pipx`, and `pip` as supported consumers of the same
  standard Hatchling distributions, recommending isolated command installs
  without making uv a runtime requirement.
- Retain immutable tagged-Git installation until the production index release;
  do not claim that package-name installation is available early.
- Change no runtime source, dependency, workflow, live configuration, hosted
  environment, or package index.

## 0.3.3 — build-once release artifact promotion

Planned:

- Build and validate the wheel and source archive once in a read-only release
  job, then upload one explicitly named workflow artifact.
- Require later release jobs to download that exact artifact rather than
  rebuilding or publishing ambient `dist` contents.
- Separate GitHub Release write permission from the build job, keep action
  references pinned to immutable commits, and retain the existing tag identity,
  ancestry, documentation, test, privacy, and version gates.
- Add package-description validation, exact two-file membership, and recorded
  hashes before any publication job exists.
- Keep TestPyPI, PyPI, OIDC permission, hosted environments, accounts, and
  package-name installation outside this release.

## 0.3.4 — trusted TestPyPI publication and verification

Planned:

- Configure a dedicated manually approved TestPyPI environment and pending
  trusted publisher only after the exact reviewed workflow identity is known.
- Publish the v0.3.4 build artifact with short-lived OIDC identity and no stored
  package-index credential.
- Verify index-reported hashes, exact-version installation, and the isolated
  ten-row self-test after bounded propagation retries.
- Do not publish to production PyPI or claim package-name installation there.

## 0.3.5 — trusted production PyPI publication and verification

Planned:

- Configure a separate manually approved production environment and pending
  trusted publisher for the reviewed workflow.
- Permit production publication only after the same artifacts pass the build,
  GitHub Release, TestPyPI, and installation-verification boundaries.
- Publish without a stored API token, verify production hashes and installation,
  and then make package-name `uv tool`, `pipx`, and `pip` commands current.
- Treat an immutable publication mistake as a new patch; never replace or reuse
  an uploaded filename.

## 0.4.0 — explicit host-acquisition architecture

Planned:

- Confine host-specific payload and transcript interpretation to an acquisition
  layer with an explicit internal interface.
- Keep rendering, storage, ledger arithmetic, paths, and host-independent probes
  free of new Claude-specific assumptions.
- Inventory Codex's local JSONL evidence with privacy-neutral fixtures before
  specifying token, session, or cost fields; post-hoc approximate cost analysis
  is not sufficient evidence for a currency-labelled runtime claim.
- Re-check Codex's current declarative footer and hook interfaces before choosing
  an implementation. Do not claim this command renderer runs in Codex unless an
  installed interface actually supports arbitrary-command status output.
- Document credible future adapters without shipping a speculative host adapter.
