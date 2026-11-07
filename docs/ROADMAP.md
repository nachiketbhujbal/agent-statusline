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
| 0.3.2 | PyPI metadata and package-page readiness | **Released** |
| 0.3.3 | Build-once release artifact promotion | **Released** |
| 0.3.4 | Trusted TestPyPI publication and verification | **Released** |
| 0.3.5 | Public README and production-ready package artifacts | **Released** |
| 0.3.6 | Separate trusted package-index promotion workflows | **Released** |
| 0.4.0 | Explicit host-acquisition architecture | **Released** |
| 0.4.1 | Normalized Claude acquisition facts | **Released** |
| 0.4.2 | Documented local session metrics | **Released** |
| 0.4.3 | Configurable context guard and Stop timing | **Released** |
| 0.4.4 | Native Linux and WSL memory pressure | **Released** |
| 0.4.5 | Session-safe context fallback and compaction counting | **Released** |
| 0.5.0 | Package-owned TOML configuration and Python 3.11 minimum | **Released** |
| 0.5.1 | Select existing field groups within each row | **Released** |
| 0.5.2 | Fit the malformed-input fallback to narrow terminals | **Released** |
| 0.5.3 | Discover valid field IDs with `config fields [ROW]` | **Released** |
| 0.5.4 | Inspect effective settings and their sources with `config show` | **Released** |
| 0.5.5 | Print starter TOML with `config example` | **Released** |
| 0.5.6 | Preview a synthetic session with `config preview --width 80` | **Released** |
| 0.5.7 | Align the configuration guide with installed versions and setting precedence | **Released** |
| 0.5.8 | Prefer native prompt-cache state and qualify legacy estimates | **Released** |
| 0.5.9 | Installer-listing readiness and the next customization milestones | **Released** |
| 0.5.10 | Host cost estimate provenance | **Current** |

0.2.1 through 0.2.14 and v0.3.0 through v0.5.9 are tagged and released. The
v0.3.0 boundary names that completed, independently proven train as the
production-ready supported public baseline. Each boundary retains its exact
review and artifact evidence; GitHub Release objects begin at v0.2.4. The
historical hardening branch remains source material and is not a merge
candidate.

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

Released:

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

Released:

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
- Lock the release-only build and package-description tools without adding a
  runtime dependency or requiring Python 3.10 for the installed command.
- Enforce least privilege, build-once behavior, exact artifact identity, and
  fail-closed promotion with deterministic policy and mutation tests.

## 0.3.4 — trusted TestPyPI publication and verification

Released:

- Configure a dedicated manually approved TestPyPI environment and pending
  trusted publisher only after the exact reviewed workflow identity is known.
- Publish the v0.3.4 build artifact with short-lived OIDC identity and no stored
  package-index credential.
- Verify index-reported hashes, exact-version installation, and the isolated
  ten-row self-test after bounded propagation retries.
- Require the TestPyPI deployment to wait for the same tag's successful build
  and GitHub Release, and keep its manual environment approval human-operated.
- Enforce the exact four-job topology, least privilege, immutable action and
  filename behavior, bounded network evidence, and isolated install through
  synthetic mutation coverage.
- Exact-map every publisher-action input and execute the installed `selftest`
  command shape in local policy evidence before the immutable upload boundary.
- Do not publish to production PyPI or claim package-name installation there.

## 0.3.5 — public README and production-ready package artifacts

Released:

- Replace the exhaustive landing-page documentation catalog and internal
  process narrative with a concise product, output, installation, safety,
  command, and contributor journey
  ([ADR 0044](adrs/0044-keep-the-readme-as-a-product-landing-page.md)).
- Preserve the detailed handoff, history, review, research, and architecture
  records in the repository without promoting every one from the README.
- Correct the existing CI scope classifier so root-level Markdown receives the
  same ancestry-only treatment as nested documentation, with executable and
  fail-closed policy regressions while preserving full scope for source changes.
- Stage plain package-name installation and update commands for the separately
  authorized production promotion.
- Produce one exact wheel/source pair that passes the build, GitHub Release,
  TestPyPI, public-hash, and isolated-install boundaries.
- Keep production upload authority out of the tag-triggered release and retain
  the immutable-filename rule for the later promotion.

## 0.3.6 — separate trusted package-index promotion workflows

Released:

- Keep tag-triggered `release.yml` responsible only for building and publishing
  the immutable GitHub Release pair.
- Add paired manual `publish-testpypi.yml` and `publish-pypi.yml` workflows that
  promote an existing annotated release tag from exact `main` without rebuilding.
- Bind the downloaded wheel and source archive to exact filenames and SHA-256
  values before the environment-gated OIDC job receives them; production also
  requires the exact pair to exist on TestPyPI first.
- Give only the two-action publisher `id-token: write`; forbid stored tokens,
  scripts, checkouts, cross-run artifacts, ambient files, and collision skips in
  that privileged job.
- Verify exact public-index files and hashes, then install the exact wheel in a
  fresh Python 3.9 environment and run the isolated self-test.
- The production lane has promoted the already proven v0.3.5 GitHub Release
  pair without repeating its TestPyPI upload or moving the v0.3.5 tag.
- TestPyPI's trusted publisher now names `publish-testpypi.yml`; both GitHub
  environments allow only branch `main`, require maintainer approval, and
  allow no bypass.
- Require fail-fast behavior inside every multi-command evidence script and
  exact-bind the ordered preparation and verification blocks so shell defaults
  or post-hash file replacement cannot bypass provenance.
- v0.3.6 passed GitHub Release, TestPyPI, and PyPI publication through the
  paired lanes. The local uv-managed command was upgraded from production PyPI
  without touching live ledger state.

## 0.4.0 — explicit host-acquisition architecture

Architecture recorded in [ADR 0046](adrs/0046-separate-host-acquisition-from-presentation.md):

- Confine host-specific payload and transcript interpretation to an acquisition
  layer with an explicit internal interface.
- Keep rendering, storage, ledger arithmetic, paths, and host-independent probes
  free of new Claude-specific assumptions.
- The current Codex footer remains a fixed widget list, while stable hooks now
  provide a credible local acquisition trigger. Hook acquisition does not make
  this command renderer available in Codex.
- A privacy-bounded JSONL inventory found exact token, session, context, limit,
  and timing evidence but no exact cost field. Codex facts therefore cannot
  update the currency ledger.
- Keep live rollouts out of tests. Future parser coverage uses privacy-neutral
  synthetic fixtures and tolerates unknown or malformed records because the
  transcript format is not a stable hook interface.
- Ship no adapter, hook, configuration change, or runtime behavior in this
  architecture release.

Follow-on patches:

- 0.4.1: introduce normalized acquisition facts and a Claude adapter without
  changing the ten-row output or installer behavior.
- 0.4.2: publish a documented, local per-session metrics contract built from
  normalized facts ([issue 30](https://github.com/nachiketbhujbal/agent-statusline/issues/30)).
- 0.4.3: make the context guard configurable and offer actionable Stop timing
  without forcing Claude to continue ([issues 31](https://github.com/nachiketbhujbal/agent-statusline/issues/31)
  and [32](https://github.com/nachiketbhujbal/agent-statusline/issues/32)).
- Defer the synthetic-fixture Codex rollout parser and any opt-in collector/query
  surface until after this local integration sequence.
- Defer Codex footer rendering until an arbitrary-command interface exists, and
  defer Codex currency accounting until the host supplies exact attributable
  cost.

## 0.4.1 — normalized Claude acquisition facts

Released:

- Add one internal, dependency-free acquisition interface grouped by identity,
  workspace, model, context, tokens, limits, activity, and exact money.
- Adapt Claude's payload and transcript evidence into that interface, omitting
  facts the host does not supply.
- Make the existing renderer consume the adapter without changing its ten rows,
  fields, ordering, ledger, installer, hooks, or state files.
- Keep the interface internal until 0.4.2 defines the supported public session
  metrics schema ([ADR 0047](adrs/0047-normalize-claude-acquisition-facts.md)).

## 0.4.2 — documented local session metrics

Released ([issue 30](https://github.com/nachiketbhujbal/agent-statusline/issues/30)):

- Publish one versioned, private, atomically replaced snapshot per non-empty
  session identifier on every render.
- Expose the supported snapshot through `agent-statusline metrics <session-id>`
  so integrations do not parse internal transcript or ledger state.
- Include only accountable normalized facts. In particular, expose lifetime
  session cost only when the current host cost and ledger history are exact.
- Bound snapshots to 35 days and 512 sessions, and support an environment opt-out.
- Prove the shape with synthetic self-test, missing-evidence, retention, and
  concurrent-session coverage ([ADR 0048](adrs/0048-publish-versioned-local-session-metrics.md)).

## 0.4.3 — configurable context guard and Stop timing

Released ([issues 31](https://github.com/nachiketbhujbal/agent-statusline/issues/31)
and [32](https://github.com/nachiketbhujbal/agent-statusline/issues/32)):

- Make the context warning threshold and message configurable with safe defaults.
- Let the guard use the documented per-session snapshot rather than a global
  last-render payload when a session identifier is available.
- Support actionable Stop-time warnings without forcing another model turn.
- Retain prompt-submit warnings as an explicit option and validate every
  setting through the installed synthetic self-test
  ([ADR 0049](adrs/0049-configure-context-warnings-at-stop-time.md)).

## 0.4.4 — native Linux and WSL memory pressure

Released ([ADR 0050](adrs/0050-report-native-linux-memory-pressure.md)):

- Preserve the existing macOS `sysctl` and `vm_stat` memory calculation.
- On Linux, derive pressure from `MemTotal - MemAvailable` in `/proc/meminfo`
  and normalize it to the renderer's existing memory fields.
- Under WSL, report against the capacity visible to the Linux environment rather
  than the Windows host's full physical RAM.
- Retain graceful omission when required evidence is unavailable or malformed,
  and keep compressed-memory detail macOS-only.
- Certify both native platform paths in hosted CI without dependencies or a
  display-layout change.

The independently reviewed implementation passed protected PR and merged-main
Linux/macOS CI, annotated v0.4.4 GitHub Release creation, and exact TestPyPI and
production PyPI publication with clean Python 3.9 installation evidence.

## 0.4.5 — session-safe context fallback and compaction counting

Released ([ADR 0051](adrs/0051-keep-context-fallback-and-compactions-session-scoped.md)):

- Keep the session metrics snapshot as the context guard's preferred source.
- Accept a last-payload window only for the matching session, or matching
  transcript when the hook lacks a session ID. Omit the warning when a window
  cannot be established; never guess one million tokens or borrow another chat.
- Count explicit compaction boundaries and pair their summaries once, including
  pairs split across redraws. Preserve summary-only transcript support.
- Rebuild older transcript caches and verify independent counts and context
  warnings through six concurrent synthetic renderer/hook processes.
- Preserve all ten rows, exact accounting, private locked storage, dependencies,
  installer behavior, and live user configuration.

Package-owned configuration shipped separately in v0.5.0.

The implementation is independently reviewed and merged through PR #39. Exact
PR and merged-main Linux/macOS CI passed, and annotated v0.4.5 and its GitHub
Release pair are verified. TestPyPI published and verified the same pair.
Production PyPI published and verified the identical pair after its separate
maintainer approval. GitHub Release run 40043218170, TestPyPI run 40043331875,
and PyPI run 40043731533 passed; the v0.4.5 release scope is complete.

The post-tag closure also corrects the development documentation verifier to
accept a fully released roadmap with no selected next target. Version agreement
and review/privacy checks remain enforced; no successor release is invented.

## 0.5.0 — package-owned TOML configuration

Released. [ADR 0052](adrs/0052-add-opt-in-toml-configuration-at-v0-5.md)
defines the contract and acceptance evidence.

- Raise the minimum to Python 3.11 and use its TOML reader with no runtime
  dependencies. Keep 0.4.x on Python 3.9+ without TOML; no configuration
  prerequisite or follow-up patch is planned on that line.
- Add optional user configuration for existing context warnings and metrics
  enablement, retaining defaults and existing environment precedence.
- Add plain output, explicit `"show"` / `"hide"` row visibility and read-only
  `config check`. Preserve default output, data collection and accounting.
- Verify installation and behavior using disposable state and Claude settings.
  Field selection shipped separately in v0.5.1.

PR #42, exact merged-main CI, annotated tag, GitHub Release, TestPyPI and
production PyPI verification passed.

## 0.5.x — display customization

- **Field visibility.** Choose existing field groups without changing row
  switches, field priority, collection, or accounting. See
  [ADR 0053](adrs/0053-select-existing-display-field-groups.md).
- **Fallback width.** Fit the existing malformed-input stub to the terminal
  in both styled and plain modes.
- **Field discovery.** List all supported field IDs or the IDs for one row,
  with descriptions from the same catalog the validator uses. See
  [ADR 0054](adrs/0054-list-supported-display-field-ids.md).
- **Effective configuration.** Show resolved settings and their sources.
  Report invalid-file fallback and omit free-text values. See
  [ADR 0055](adrs/0055-show-effective-configuration.md).
- **Starter TOML.** Print a commented example that validates as printed
  and preserves defaults when saved. See
  [ADR 0056](adrs/0056-print-starter-toml.md).
- **Synthetic preview.** Render sample session data at the requested width
  using effective display settings and the regular renderer. See
  [ADR 0057](adrs/0057-preview-synthetic-status-line.md).

Each patch has one purpose. A verified defect can take the next available
patch number at any point in the series. Shift the remaining planned features
forward in order and retain the already released versions.

Use the verified GitHub Release on `main` as the baseline for the next
patch. Record TestPyPI and PyPI promotion separately until each is verified.
The two maintainer approvals and the requirement to verify TestPyPI before
production still apply. See [ADR 0045](adrs/0045-promote-github-releases-through-separate-package-index-workflows.md).

The planned customization work and documentation patch are published and
verified on GitHub, TestPyPI, and production PyPI. The
[handoff](../HANDOFF.md#resume-point) links the per-version publication evidence.

## 0.5.7 — configuration guide alignment

Released and verified on GitHub, TestPyPI, and production PyPI.

Document which installed versions support each configuration feature.
Align the upgrade instructions and the context warning and metrics guides
with the shipped TOML and environment behavior.


## 0.5.8 — native prompt-cache reporting

Released and verified on GitHub, TestPyPI and production PyPI after the full
local gate, exact independent review, Linux/macOS CI and installed-artifact
verification. The [handoff](../HANDOFF.md#resume-point) links both completed
package promotions and their exact artifact hashes.

- Prefer validated `prompt_cache` TTL, warmth and expiry from Claude Code
  v2.1.251+; use only the current session payload, never shared last-payload state.
- Retain older-client transcript fallback, explicitly qualify estimated expiry,
  and remove the claim that every expired prefix forces a full resend.
- Treat five minutes as a supported TTL, without inferring billing trouble.
- Preserve rows, field IDs, default collection, accounting and configuration.
- Verify native precedence, expiry boundaries, missing or malformed optional
  signals, no-transcript rendering, separate sessions, plain output and width.

See [ADR 0058](adrs/0058-prefer-native-prompt-cache-state.md).

## Further host coverage — one opt-in slice at a time

The [capability inventory](RESEARCH.md#claude-code-status-line-capability-audit)
separates supported facts from gaps. Their planned slots now appear below;
inventory alone does not imply implementation. Each host-field slice documents
source, scope, client minimum, absence, freshness and opt-in selection. Preserve
the existing default field set and keep native host facts separate from local
ledger evidence. Never use runtime network APIs to fill absent facts.

## Next release and milestones

The maintainer approved a richer view model and an early interactive editor,
while retaining one opinionated configuration location. See
[ADR 0060](adrs/0060-evolve-one-config-with-collection-independent-views.md) and
[the design](CUSTOMIZATION_DESIGN.md) for contracts and acceptance evidence.
Collection and calculation always precede display choices: hiding a cost period
must never stop its accounting. No profiles or alternate config-path switches.

**0.5.9** is verified on GitHub and TestPyPI; production approval/publication
remains pending. Subsequent numbers are ordered
planning slots, not release dates or shipped features. A concrete fix can take
**any** next patch number and shift all following planned patches. Reassess
milestone boundaries as evidence develops; do not manufacture releases to fill
a version range or bundle independent features to meet these labels.

### 0.5.9 — installer-listing readiness and forward design

Released and verified on GitHub after the complete gate, independent exact-SHA
review and Linux/macOS CI. The exact wheel passed clean installation and an
isolated self-test. See the [handoff](../HANDOFF.md#resume-point) for hashes and
the verified TestPyPI promotion and pending production approval.

- Require exact non-yanked wheel/source hashes in the installer's Simple JSON
  listing as well as release JSON before clean index installation. Poll both
  within the existing bounded verification window. Cover the observed delayed
  listing regression synthetically for both package indexes.
- Preserve exact artifacts, separate approvals, clean installation/self-test
  and verification-only retries. No upload retry or runtime networking.
- Publish the customization/refresh design, dated comparison and focused
  milestones; align README, field/porting pointers, ADRs and current records.
- No runtime rendering, configuration schema, ledger or Claude settings changes.

See [ADR 0059](adrs/0059-verify-installer-listing-before-index-install.md).

### Remaining 0.5.x — correctness, refresh and measured speed

| Planning slot | One primary change | Evidence required before release |
| --- | --- | --- |
| 0.5.10 | Clarify host-reported cost versus invoice/billing truth | Source qualifiers in display/docs; retained totals, `≥`, resume and rolling-window parity; no ledger rewrite |
| 0.5.11 | Correct relative cache-cost multipliers for supported TTL/model facts | Explicit inputs and assumptions; mixed-TTL fixtures; unknown pricing omits ratio instead of inventing it; no derived dollars |
| 0.5.12 | Opt-in host-supported timed refresh | Explicit installer set/remove with dry-run; preserve omitted interval and unrelated settings; repeated-payload idempotence and idle cross-session rolling totals |
| 0.5.13 | Optimize demonstrated render overhead under frequent redraws | Paired installed cold/warm/import and six-session measurements; retain probes, accounting and isolation; record no-change result if no justified optimization exists |

No schema-2 work is hidden in a 0.5.x patch. Existing schema-1 files, group IDs,
default view and environment overrides remain compatible. Refresh uses Claude's
timer, not a daemon. One-second host support does not guarantee one-second
remote facts. Performance is measured with full collection, not by dropping
hidden metrics. No timing-only release is required without a useful change.

### 0.6.x — finer controls and the interactive editor

0.6.0 is the stable richer configuration boundary. 0.6.1 is deliberately the
first follow-up: users get a useful editor before themes, layouts or every
possible host field is complete. New controls extend the same editor and catalog.

| Planning slot | One primary change | Acceptance boundary |
| --- | --- | --- |
| 0.6.0 | Schema-2 element visibility within current compound groups | Accept schema 1 unchanged; keep row `show`/`hide` and group gates; independent 24h/7d/30d visibility; shared discover/check/show/example/preview catalog; hidden/re-shown collection parity |
| 0.6.1 | Interactive `config edit` for the shipped view controls | Synthetic preview, undo, source indicators, diff, explicit save/cancel, comment preservation, migration and concurrent-edit refusal; no live state or implicit Claude settings writes |
| 0.6.2 | Opt-in native cache performance elements | Requests, misses, expected rebuilds, hit ratio and recache counters with documented host scope; absent versus zero and no change to ledger |
| 0.6.3 | Opt-in native cache miss diagnostics | Last miss, host-reported cause and age; unknown-cause and older-client behavior, no inferred blame |
| 0.6.4 | Typed labels, symbols, number/unit/path/time formatting | Finite catalog choices; preserve source/estimate/lower-bound qualifiers; Unicode/ASCII and plain width parity |
| 0.6.5 | Accessible semantic colors and visual thresholds | Product-defined palettes/roles; warnings work without color; plain output wins; context guard stays independent |
| 0.6.6 | Bounded conditional visibility | Available/nonzero/active and typed thresholds, no expression language; missing is not zero; collection unchanged |
| 0.6.7 | Opt-in main-conversation agent/prompt identity | Session-scoped host facts with client availability; no subagent-protocol claim |
| 0.6.8 | Opt-in native repository/worktree identity | Distinguish current and origin workspace facts, preserve local Git fallback and session identity |
| 0.6.9 | Opt-in PR/MR and review-state elements | Native payload only, safe links, missing/stale state, no runtime network lookup |
| 0.6.10 | Opt-in Vim/editor mode | Native mode availability; installer indicator changes only through an explicit separately previewed choice |
| 0.6.11 | Opt-in additional context detail | Inventory concrete native counters first; distinguish current window from lifetime throughput |
| 0.6.12 | Opt-in gateway spend-limit percentages/period | Availability and scope, missing/zero semantics; no estimated dollars in the exact ledger |

Field IDs, formatting keys and host minimums are finalized in the relevant
slice-specific ADR and field documentation before implementation. If a host
contract cannot be proven, defer that item without blocking unrelated controls
or the editor. Each compatible addition is opt-in; it cannot enlarge defaults.

### 0.7.x — optional layouts with the same opinionated defaults

| Planning slot | One primary change | Acceptance boundary |
| --- | --- | --- |
| 0.7.0 | Optional ordering of existing canonical rows | Default ten-row order unchanged; complete duplicate-free order; schema compatibility and deterministic width fitting |
| 0.7.1 | Optional per-row element ordering | Stable IDs and explicit priority under width pressure; no arbitrary rows, templates or duplicate metrics |
| 0.7.2 | Layout editing in the interactive editor | Keyboard reorder, preview/diff/reset/undo and lossless save reuse the existing configuration transaction |
| 0.7.3 | Product-defined density, separators and wrap choices | Finite options; terminal-cell bounds across ANSI/ASCII/Unicode and narrow widths; qualifiers survive fitting |

These are view changes only. The editor is already available from 0.6.1.
Layouts do not select acquisition behavior, create profiles or move the file.
If this work is smaller than expected, revise the milestone rather than padding
the series. Custom rows and programmable formatting remain separate ideas.

### 0.8.x — proven additional host acquisition

| Planning slot | One primary change | Acceptance boundary |
| --- | --- | --- |
| 0.8.0 | Local non-currency Codex acquisition | Reverify current official interface; synthetic schema-tolerant fixtures, host-namespaced state and explicit hook installation; no command-renderer claim |
| 0.8.1 | Public query of the new host's supported metrics | Versioned host/source/freshness contract and absence semantics; no collision with Claude identities or money |
| 0.8.2 | Claude subagent status-line adapter | Separate batch input/JSONL output, task identity and explicit opt-in managed installation; no parent/child metric crossover |

This is a capability-dependent milestone, not a promise that Codex will accept
an arbitrary renderer. Revalidate [PORTING.md](PORTING.md) at implementation.
Third-host adapters need a current official contract and a real use case before
receiving a release slot. Acquisition, presentation and monetary evidence stay
independent. There is no forced 0.9 milestone; further scope follows evidence.
