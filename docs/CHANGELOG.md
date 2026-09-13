# Changelog

This project follows semantic versioning. Versions come from immutable Git tags
([ADR 0019](adrs/0019-release-tags-are-immutable.md)); there is no version
string in the source.

## Unreleased — 0.3.5

The public README is now a focused product landing page and package-index
description rather than an inventory of internal project records. It leads with
the complete status-line output, the short installation and verification path,
the data shown, local privacy and exact-money guarantees, common commands, and
concise update, removal, and development guidance. Detailed handoff, release,
review, research, and architecture history remains tracked in the repository
without being promoted as the prospective user's primary journey
([ADR 0044](adrs/0044-keep-the-readme-as-a-product-landing-page.md)).

The unmerged candidate stages production package-name commands for `uv tool`,
`pipx`, and `pip`. Production PyPI configuration, publication, merge, tagging,
and release remain unapproved and must not occur until the maintainer accepts
the public copy and separately authorizes that boundary.

Independent review corrected the retained output example so its process-memory
percentage, memory bar, and named tool counts agree with the renderer. It also
distinguishes atomically replaced state from the rate-limit log's locked,
durable append path rather than overstating one persistence mechanism for every
state file.

The CI documentation-only classifier now explicitly excludes root-level
Markdown as well as nested documentation. Executable regressions prove that
`README.md`, `HANDOFF.md`, and nested docs retain the ancestry-only lane while a
source change still selects the full Linux and macOS gate. Public-readiness
policy pins the exact reviewed path boundary so the mismatch cannot silently
return.

Independent review then demonstrated that checking only the diff line and the
presence of both output strings would still accept a changed base expression or
a trailing `full=false` override. The policy now exact-matches the complete
scope step, and mutation tests reject both bypasses before either could skip
required source or workflow evidence.

## 0.3.4

The release pipeline now sends the exact build-once artifact pair to TestPyPI
through a dedicated manually approved environment and a short-lived trusted
publishing identity. The publication job waits for both the read-only build and
GitHub Release, receives only `id-token: write`, downloads the named artifact,
and invokes one immutable-pinned PyPA action. It cannot rebuild, execute a
script, read a stored package-index credential, skip an existing filename, or
target production PyPI.

A separate read-only job polls the version-specific TestPyPI JSON endpoint
within fixed attempt, delay, response-size, and request-timeout limits. It
requires the exact v0.3.4 project, wheel/source filenames, distribution types,
and build-job SHA-256 hashes. It then installs the exact wheel from TestPyPI in
a fresh Python 3.9 environment with no dependencies or source fallback,
verifies the command version, and runs the installed self-test against
disposable state. Deterministic policy and unit tests fail closed on privilege,
topology, endpoint, artifact, retry, credential, and isolated-install drift
([ADR 0043](adrs/0043-publish-exact-artifacts-to-testpypi-with-gated-oidc.md)).
Independent review additionally proved and corrected the installed command from
the invalid `--selftest` option to the real `selftest` subcommand, then required
exact input maps for both publisher actions so quoted credentials,
collision-skipping aliases, and cross-run or cross-repository artifact sources
fail closed.
The command-shape regression explicitly loads this checkout's source, so it
also passes in the Release job's deliberate `--no-install-project` environment
from an unrelated working directory.

Production PyPI, production package-name installation, runtime behavior,
runtime dependencies, display, accounting, live Claude Code, and Codex host
work remain outside this release.

## 0.3.3

The tag-triggered pipeline now builds and validates one exact wheel/source pair
inside a read-only job using the committed uv lock and exact uv version. It
records exact filenames and SHA-256 hashes, transports only one workflow
artifact named for the tagged commit, and rejects additional, symlinked,
renamed, version-disagreeing, or hash-disagreeing files.

Only the dependent GitHub Release job receives repository-content write
permission. That job downloads and verifies the named pair without rebuilding,
then publishes two explicit paths rather than ambient `dist` contents. The
public-readiness policy and synthetic mutations fail closed if future edits
weaken permissions, dependency order, build uniqueness, artifact identity, or
the exclusion of package-index authority. Release-only Twine 7 removes the
v0.3.2 local/hosted metadata-checker mismatch without changing the package's
empty runtime dependency set or Python 3.9 support
([ADR 0042](adrs/0042-build-once-and-promote-exact-release-artifacts.md)).

TestPyPI, production PyPI, OIDC, hosted environments, accounts, credentials,
package-name installation, runtime behavior, and live Claude Code remain
outside this release.

## 0.3.2

The public package surface now names standard source, issue, documentation, and
changelog URLs. README links are absolute so the same long description remains
usable when rendered outside the GitHub repository, including a future package
index page.

Installation guidance now distinguishes package format from package manager:
`uv tool` remains the recommended isolated command installation, `pipx` offers
the same isolation model, and `pip` is supported in the selected Python
environment. Until production PyPI publication lands in its own release, all
three continue to install from the immutable public Git tag. This release does
not change runtime code, dependencies, workflows, live configuration, or any
package index ([ADR 0041](adrs/0041-stage-pypi-distribution-as-independent-patches.md)).

## 0.3.1

A fresh renderer process no longer imports `argparse`, `subprocess`, or
`shutil`. Ledger argument parsing and probe subprocess support load only when
those colder paths execute; terminal-width detection keeps its environment,
positive terminal, and fallback behavior without `shutil`. An unusable
zero-column terminal result now consistently selects the existing fallback on
every supported Python version; Python 3.9 previously returned zero at that
edge. Atomic state publication now creates the same private, exclusive,
same-directory temporary directly, with a bounded collision retry and unchanged
lock, flush, replacement, cleanup, and permission guarantees
([ADR 0040](adrs/0040-remove-avoidable-hot-path-imports.md)).

The new isolated benchmark command reports interpreter, import-only, warm, and
cold timing distributions plus the warm/interpreter ratio. Results remain
informational rather than a wall-clock CI gate. Deterministic tests enforce the
import budget and terminal-width/storage behavior. Benchmark children load the
exact checkout source explicitly, so the command does not depend on an editable
or wheel installation. Apart from the unusable zero-width normalization, the
approved ten rows, fields, priorities, runtime dependencies, accounting, and
live configuration are unchanged.

## 0.3.0

The independently reviewed and released v0.2.1 through v0.2.14 hardening train
is now the explicit production-ready supported public baseline. The historical
integration branch remains superseded source material and is not merged into
this release.

The package maturity classifier now reports `Production/Stable`, and the normal
no-clone installation and upgrade commands point at the immutable v0.3.0 Git
tag. This milestone changes no runtime source, renderer output, approved row or
field, dependency, installer, workflow, state, or live configuration. PyPI
publication remains a separate future decision.

## 0.2.14

Full-scope pull requests, `main` pushes, and manual runs now add one automatic
macOS lane to the complete Linux Python matrix. The stable branch-protection
result requires both hosted test lanes to pass for full scope and both to be
deliberately skipped for documentation-only scope; missing, failed, cancelled,
or inconsistent results fail closed. The public-readiness verifier locks that
topology and the macOS test/probe evidence in place.

Current documentation now reflects the public repository and released v0.2.13
boundary. Normal users install the command-line tool directly from an immutable
public Git tag without manually cloning; a future package-name install still
requires a separate PyPI publication. Runtime behavior, the ten-row renderer,
dependencies, live state, and current installed wiring are unchanged.

## 0.2.13

Artifact and reachable-history privacy checks now fail closed on every regular
member or blob above the two-MiB audit boundary instead of silently skipping
it. Synthetic regressions cover both paths, and a renewed strict scan confirms
that the ordinary reachable graph contains no oversized blob.

The historical Actions exposure inventory downloaded and scanned all retained
run logs and artifacts. Sixteen unsafe CI source-distribution artifacts carrying
the superseded ADR 0018 billing phrase were deleted with explicit authorization.
The post-deletion snapshot verified all 41 then-retained logs and all ten
remaining artifacts in a complete second scan. Current tracked records now
reflect the released v0.2.12 boundary and the completed public baseline.

The repository is public. Active no-bypass ruleset `22966865` protects `main`
with mandatory pull requests and resolved review threads, a strict required
GitHub Actions result, and blocked deletion and force-push. CI exposes one
stable aggregate result that requires the always-on policy job and either the
complete Python matrix or its deliberate documentation-only skip. The
aggregate accepts only explicit full or documentation-only scope, fails closed
on missing or malformed scope, requires the exact unconditional job condition,
enables its own fail-fast shell behavior, and cannot be made conditional,
non-blocking, or shell-overridden without failing repository policy. Only the
reviewed canonical direct keys are accepted on the aggregate job and enforcement
step, so quoted, escaped, whitespace-varied, duplicate, or unexpected keys fail
closed. Runtime behavior, dependencies, Git history, release tags and assets,
and live state are unchanged.

## 0.2.12

Public documentation now matches the released package boundary, including the
installer's conditional timestamp hooks, isolated self-test, failure breadcrumb,
state guarantees, and current Codex footer limitations. A tracked public-
readiness record covers history and refs, artifacts, repository settings,
secrets and environments, hosted evidence, and the separately authorized
visibility/protection sequence.

Every third-party workflow action is pinned to a reviewed full commit SHA with
a readable release comment. A dependency-free policy check enforces immutable
action refs, the lean CI trigger/permission boundary, absence of the undefined
dependency prefix, root ignores for `/.claude/`, `/.pvt/`, and `/.worktrees/`,
and removal of exact private billing evidence from the current tree. ADR 0033
supersedes the earlier private-billing record while retaining conservative
private CI and explicit authorization for visibility or repository-setting
changes.

GitHub and repository-local no-reply controls now prevent another maintainer
merge from exposing a personal address. Automatic `main` CI validates the
generated merge identity, Release validates the annotated tagger and peeled
commit before publication, artifact policy scans archive contents, and a
deterministic audit covers ordinary reachable branches and tags. The ADR 0034
one-time rewrite and historical Release repair are complete. Twelve immutable
GitHub-managed historical pull heads remain as the explicitly accepted ADR 0035
residue.

CI now audits the complete ancestry of every pull request and `main` push,
including documentation-only refs, while skipping the expensive gate for
documentation-only changes. Release audits the tagged commit's complete
ancestry before publication. The policy verifier enforces both workflow steps,
full checkout history, and the absence of path filters that could bypass the
audit. Runtime behavior and dependencies are unchanged.

## 0.2.11

`agent-statusline selftest` now renders the v0.2.10 synthetic contract in a
fresh child process with isolated private home, configuration, state, and
working directories. It derives expected labels from authoritative `ORDER`,
verifies all ten rows and private regular state entries, suppresses child output,
and runs against the installed wheel in CI
([ADR 0029](adrs/0029-self-test-with-isolated-state-and-safe-failure-evidence.md)).

Unexpected renderer exceptions now leave a private atomic breadcrumb containing
only schema, UTC time, fixed phase, and exception type before the original error
continues. Messages, tracebacks, payloads, paths, commands, and filenames are
excluded; malformed input and routine closed pipes create no breadcrumb, and a
breadcrumb write failure cannot mask the renderer failure. Runtime dependencies
remain empty.

## 0.2.10

A committed privacy-neutral payload and transcript now drive the same exact
renderer contract in pytest and in CI's installed-wheel smoke. Runtime
materialization replaces template paths and assistant/reset clocks with current,
absolute values inside a disposable workspace. Both environments isolate
`HOME` and `AGENT_STATUSLINE_STATE`, render from an unrelated working directory,
and require all ten labels in `ORDER` plus transcript-derived cache, token, tool,
and timing evidence ([ADR 0028](adrs/0028-gate-the-installed-renderer-with-synthetic-evidence.md)).

CI now builds once and installs that wheel without dependencies before the
installed-shape smoke. Artifact policy requires the evidence in the source
distribution and excludes it from the runtime wheel. Runtime behavior and
dependencies are unchanged.

## 0.2.9

Rendering now measures printable terminal cells rather than code-point count,
so wide and combining Unicode remain within the physical width budget. Every
label, separator, and segment is sanitized before fitting: only the package's
exact SGR styles survive, while other escapes, line controls, format controls,
and bidirectional controls are removed. Clipping stays on complete code-point
boundaries, and continuation indentation is retained under the host's observed
leading-whitespace behavior ([ADR 0027](adrs/0027-measure-cells-and-sanitize-terminal-output.md)).

Nested Git branch discovery no longer changes the current-workspace path used
by the `SYSTEM` disk probe. The 5h/7d allowance value is now a floored integer,
preventing a fractional value below 100 from displaying early exhaustion; the
burn-rate decimal and numeric overage boundary are unchanged.

## 0.2.8

Project authority and continuation state are now recoverable from tracked,
public-safe files. `AGENTS.md` is the authoritative instruction record,
`HANDOFF.md` is the concise current-state record, and research is separated from
release commitments. [ADR 0026](adrs/0026-coordinate-one-owner-and-one-reviewer.md)
establishes one branch owner and one independent reviewer, serial review with at
most one reviewer active, owner-only corrections, and renewed exact-SHA review
after any correction.

A deterministic documentation check validates relative Markdown links, ADR
index/file agreement and intentional reservations, release-version agreement,
the ownership/review boundary, and public-safe governance text. Runtime,
rendering, installation, accounting, storage, live configuration, workflow
triggers, and repository visibility are unchanged.

## 0.2.7

Ephemeral observation state now has explicit lifecycle bounds
([ADR 0025](adrs/0025-bound-ephemeral-observation-state.md)). Probe rows expire
after seven days and the active row plus the 255 newest remaining observations
are retained. Transcript rows expire after 35 days, are capped at 512 while
preserving the active transcript, and update their access time no more than
hourly. Legacy transcript rows receive a safe first-access timestamp so they
can age out without being discarded during migration.

The diagnostic rate-limit history is compacted at one MiB under its existing
exclusive lock and atomic publication path. Compaction discards malformed rows
and retains the newest whole valid records that fit, always preserving the
newest observation. Unchanged histories below the boundary still inspect only
the tail. Private modes, final-entry refusal, failure cleanup, transcript
offset/totals coupling, all output rows, and accounting semantics are unchanged.

## 0.2.6

Process evidence on the `SYSTEM` row is now cached by the host's opaque session
identifier, with a separately namespaced parent-PID fallback when the identifier
is unavailable ([ADR 0024](adrs/0024-scope-process-probes-by-session.md)). Two
concurrent sessions can no longer display each other's PID, process count, or
resident memory during the probe TTL. Per-session and machine-wide values still
come from one process snapshot, the existing eight-second reuse remains intact,
and cache-retention limits remain the separate v0.2.7 boundary.

## 0.2.5

Rolling `24h`, `7d`, and `30d` costs now use timestamped positive lifetime
deltas instead of assigning an entire session lifetime to its latest update
([ADR 0022](adrs/0022-account-rolling-costs-with-timestamped-deltas.md)).
Existing lifetimes migrate as non-accrual seeds: provably in-window amounts are
included, ended-before amounts are excluded, and uncertain amounts produce an
exact `≥` lower bound. Assistant timestamps drive attribution when available,
with observation fallback and a future-time clamp. Each horizon decides
completeness independently, invalid or non-finite evidence cannot make an exact
claim, and valid journal evidence is retained for 35 days.
Schemaless partial journals are preserved as incomplete evidence rather than
silently replaced, and a storage failure before the ledger updater runs marks
current-payload-only rolling amounts as lower bounds.
String session identifiers remain opaque and backward compatible, including a
legacy empty-string key. A first-sighting seed receives a start time only from
a positive, representable host duration; missing or unusable duration remains
explicitly unattributed.
UTC assistant timestamps ending in `Z` are normalized for consistent
attribution on every supported Python version.
Journal clocks use their documented whole-second precision for inclusive
cutoffs, and an event observed before its journal start keeps every window
incomplete and cannot be pruned as valid history.

Lifetime session, resume/base/run, `last5`, `all`, row order, and every non-cost
field remain compatible. Ledger mutation and event publication stay inside the
v0.2.4 locked atomic transaction; no runtime dependency is added. Source-
distribution paths are now root-anchored, and both CI and Release reject
archives containing private Relay views, local worktrees, or repository state.

## 0.2.4

Package-owned runtime state is now private and serialized through one
dependency-free storage service
([ADR 0021](adrs/0021-lock-and-privatize-runtime-state.md)). Ledger, transcript,
probe, payload, context-hook, session-close, and rate-history updates use
per-file advisory locks; replacement writes use unique same-directory `0600`
temporary files, flush and sync before atomic publication, and leave prior bytes
intact on ordinary publication failure. New state roots are `0700`, state and
lock files are `0600`, and final symlink or non-regular state entries are
refused rather than followed.

Malformed nested package caches and decoder resource errors fall back safely
without losing valid siblings. State-root setup is deferred until storage is
actually used, so an unusable optional root or transcript-cache failure no
longer suppresses stateless rendering; unsafe entries and failed writes remain
refused. Transcript offsets are reused only with mapping-shaped totals, avoiding
silent zero totals when malformed cache state requires replay. Concurrent
ledger, transcript, probe, and rate-history writers preserve their accepted
per-file semantics, including exact computed results when publication fails
after an update has run. Atomicity is per file, not across files; deliberate
same-user pathname races and Windows support remain outside the practical
local-tool boundary. All ten output rows, valid display behavior, and existing
cost-accounting semantics are unchanged; no v0.2.5 accounting model is included.

## 0.2.3

Malformed but valid JSON from the host now degrades safely instead of removing
the status line ([ADR 0032](adrs/0032-normalize-malformed-host-input-at-the-boundary.md)).
Non-object payloads use the minimal fallback, non-object transcript rows are
ignored while later valid rows still count, and bounded finite coercion protects
payload, transcript, and formatter numeric paths. Invalid path, sequence,
permission-mode, and session-identifier shapes now fall back safely as well,
and transcript conversation identifiers and tool names can no longer poison
incremental or accounting state. Valid output is unchanged and an absent cost
is not converted into zero.

## 0.2.2

Establish the locked, reproducible local development and release gate
([ADR 0023](adrs/0023-use-a-locked-local-quality-gate.md)): a committed
`uv.lock`, pre-commit hooks running Ruff, Black, and mypy from the locked
environment, and subprocess-aware coverage measurement. Tooling only --
runtime behavior, dependencies, and the build backend are unchanged.
Formatting is no longer exempted for dense render code; source layout was
never part of the status-line output contract.

## 0.2.1

Installation and removal now mutate only configuration this package owns
([ADR 0020](adrs/0020-own-only-managed-configuration.md)). Also records the
practical local-tool threat model this and future installer hardening is
evaluated against ([ADR 0031](adrs/0031-practical-local-threat-model.md)).

- Preserve unrelated top-level settings, hook events, hook groups, matchers, and
  their order. Only the managed `statusLine` entry and the managed hook commands
  are added or removed.
- Fail closed on an unreadable, non-UTF-8, malformed, or non-object
  `settings.json`, and on a non-object `hooks` container. The existing file's
  bytes are left exactly as they were and no replacement is written.
- Preserve a `statusLine` entry or a `~/.claude/statusline` symlink whose
  ownership cannot be proven, rather than removing it on uninstall.
- Publish `settings.json` through a symlink instead of replacing it, and take
  the file mode from the resolved target, so a link inside the configuration
  directory keeps its indirection and settings are no longer widened to the
  symlink's own permissions. A link resolving outside the configuration
  directory is refused, with the resolved path named, rather than followed.
- Decide ownership by the exact commands this installer writes: the checkout
  form is anchored to the selected configuration directory *and* the exact
  interpreter this installation would use, and the installed form to the
  absolute path of this installation's console script. A third-party status
  line or hook is no longer claimed — neither one whose files live in a
  directory named `statusline`, nor one whose program is also named
  `agent-statusline`, nor a checkout-shape command naming some other Python
  interpreter paired with the expected script path — and so is no longer
  removed on uninstall.
- Recognize the `~/.claude/statusline/...` commands written by the released
  v0.2.0 installer, so upgrading from it replaces those entries instead of
  stacking a second set of hooks beside them, and uninstalling removes them.
  The tilde is expanded before an otherwise exact comparison, so a lookalike
  path elsewhere is still not claimed.
- Refuse to install over configuration this package does not own. A `statusLine`
  belonging to another tool, or a `~/.claude/statusline` symlink pointing at one,
  stops the install with an explanation instead of being overwritten; only one
  status line can be configured, so replacing yours would be unrecoverable.
  The refusal is keyed on the presence of a `statusLine` entry, not on being able
  to read a command out of it, so an entry in an unexpected shape — a bare
  string, a list, an object without a `command` — is protected rather than
  replaced. A `statusLine` of `null` counts as nothing configured.
  Reinstalling over this package's own entry and link stays idempotent.
- Validate every schema condition an operation depends on — the settings file's
  readability and top-level type, the `hooks` container's type, and each managed
  event's container type — before the first mutation on both the install and the
  uninstall path. A refusal now leaves no checkout symlink, no backup, no
  temporary file, and no replacement behind. A non-list event container such as
  `{"SessionEnd": "valuable"}` is refused rather than raising `AttributeError`
  partway through.
- Treat an uninstall that owns nothing as a true no-op: no `{}` is created, no
  backup is written, and unrelated settings are not rewritten. Empty hook groups
  and events belonging to other tools keep their shape rather than being
  normalized away.
- Report expected filesystem failures — a read-only or missing configuration
  directory, a failed backup, a failed publication or symlink — as a concise
  error instead of a traceback, preserving the original bytes and leaving no
  temporary file behind.
- Run installation verification against a uniquely created system temporary
  directory. It previously used a fixed `<config>/.verify-state` path and always
  removed it recursively, so an install deleted a pre-existing directory of that
  name and its contents. As a result `--dry-run` now genuinely writes nothing:
  it no longer creates the configuration directory.
- Bind settings publication to an opened directory descriptor, reached without
  following a symlink at any step from the filesystem root down to the
  configuration directory and beyond it — not only below the configuration
  directory — and create, permission, and rename the temporary file relative to
  it. Confining a path and then writing through that same path left a window in
  which swapping a checked directory for a symlink redirected publication onto
  an unrelated file outside the configuration directory; the same window existed
  at the configuration root itself, one level up from where the first fix for
  this reached.
- Bind that same descriptor once per install or uninstall and reuse it for
  every read, backup, link change, and write in the same run, rather than each
  one independently re-deriving the configuration directory's location from a
  path string. Binding correctly at one point did not protect a later point
  that re-derived the location itself: an *ordinary* directory placed at the
  configuration directory's location between two of those steps was followed,
  because refusing to follow a symlink does not refuse a plain rename.
- Decide confinement before reading, not only before writing, using that same
  binding: an out-of-tree `settings.json` symlink is refused before its
  content is read, rather than being read into memory ahead of the refusal
  that follows.
- Close the temporary settings file's descriptor on every path, including a
  permission failure between creating it and handing it to Python's file
  object. That descriptor previously leaked past the resulting error, even
  though the temporary file's directory entry was correctly removed.
- Back a valid existing settings file up before any applied mutation, publish
  atomically, and leave no temporary file behind if publication fails.
- Keep reinstallation idempotent: repeated installs never accumulate duplicate
  managed hooks.
- Make the checkout symlink and the settings rewrite recoverable as a pair: if
  an expected failure interrupts an install or uninstall after one has already
  been mutated, the other's failure rolls the link back to what it was before
  that operation began — restoring a pre-existing link to its original target,
  or removing one this run just created — instead of leaving a link and
  settings that disagree about what is installed. Restoration is itself a
  filesystem operation and can itself fail in the same rare conditions; when it
  does, that failure is now printed alongside the original error rather than
  discarded, so a link and settings left disagreeing are reported rather than
  mistaken for a clean recovery.
- Preserve fields other than `hooks` on a managed hook's containing group when
  its last managed hook is removed. Ownership covers the hook entry, not a
  user's `matcher` or other metadata beside it; a group carrying only `hooks`
  is still dropped once it is empty, and this is not the already-recorded
  choice to normalize away an empty *foreign* group, which was never claimed
  in the first place.

One deliberate exception to the ownership rule: `showMessageTimestamps` is set
to `true` when absent ([ADR 0015](adrs/0015-timestamp-hooks-are-a-stopgap.md))
and is **not** removed on uninstall, because a value already present cannot be
distinguished from one this installer added. It is stated here rather than
folded into the broader claim.

## 0.2.0

First tagged release. Ten-row width-aware Claude Code status line, cost ledger,
cached probes, incremental transcript reading, both install shapes, and no
runtime dependencies.
