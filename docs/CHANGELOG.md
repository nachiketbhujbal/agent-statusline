# Changelog

This project follows semantic versioning. Versions come from immutable Git tags
([ADR 0019](adrs/0019-release-tags-are-immutable.md)); there is no version
string in the source.

## Unreleased — 0.2.13

Artifact and reachable-history privacy checks now fail closed on every regular
member or blob above the two-MiB audit boundary instead of silently skipping
it. Synthetic regressions cover both paths, and a renewed strict scan confirms
that the ordinary reachable graph contains no oversized blob.

The historical Actions exposure inventory downloaded and scanned all retained
run logs and artifacts. Sixteen unsafe CI source-distribution artifacts carrying
the superseded ADR 0018 billing phrase were deleted with explicit authorization.
The post-deletion snapshot verified all 41 then-retained logs and all ten
remaining artifacts in a complete second scan. Current tracked records now
reflect the released v0.2.12 boundary and the conditional recommendation for a
separately authorized public conversion.

Runtime behavior, dependencies, Git history, release tags and assets, workflow
runs and logs, repository visibility, protection settings, and live state are
unchanged.

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
