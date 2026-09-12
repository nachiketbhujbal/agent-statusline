# Review findings

Findings proven on the release branch that fixes them. A row is recorded only
once the regression that demonstrates it exists in this repository.

| ID | Severity | Finding | Release | Status |
| --- | --- | --- | --- | --- |
| INSTALL-001 | High | Installation rewrote `settings.json` wholesale, discarding unrelated settings and unrelated hook entries in managed events. | 0.2.1 | Resolved by [ADR 0020](adrs/0020-own-only-managed-configuration.md) and ownership-preserving regressions |
| INSTALL-002 | High | A malformed, unreadable, non-UTF-8, or non-object settings file was overwritten instead of refused. | 0.2.1 | Resolved by fail-closed loading with byte-preservation regressions |
| INSTALL-003 | Medium | Uninstallation removed a `statusLine` entry and a `~/.claude/statusline` symlink it could not prove it owned. | 0.2.1 | Resolved by managed-command matching and preservation regressions |
| INSTALL-004 | Medium | Reinstallation appended managed hooks again, accumulating duplicates. | 0.2.1 | Resolved by removing managed hooks before writing, with a repeated-install regression |
| INSTALL-005 | High | Publishing replaced a symlinked `settings.json` with a regular file, orphaning the real file it pointed at, and copied the symlink's own mode onto the new settings file. | 0.2.1 | Resolved by publishing to the resolved target, confined to the configuration directory, and taking that file's mode |
| INSTALL-006 | Medium | Install created the `~/.claude/statusline` symlink before validating `settings.json`, and uninstall removed it before validating, so a refusal left a half-changed tree either way. | 0.2.1 | Resolved by validating before any mutation on both paths, with a regression for each |
| INSTALL-007 | High | Ownership was decided by an unanchored path suffix, so a third-party tool whose files lived in a directory named `statusline` was treated as managed and removed on uninstall. | 0.2.1 | Resolved by matching the exact commands this installer writes into the configuration directory |
| INSTALL-008 | High | Following a symlink out of the configuration directory turned installation into an unconfined write, silently adding managed keys to an unrelated file. | 0.2.1 | Resolved by refusing an out-of-tree target and naming the resolved path, before any backup is written |
| INSTALL-009 | Medium | The suite read the developer's live `~/.claude.json` for a feature flag, so it passed or failed depending on machine state. | 0.2.1 | Resolved by redirecting `HOME` in `conftest` before import, with a guard test |
| INSTALL-010 | High | Installed-shape ownership matched a bare basename, so any command whose program was named `agent-statusline` was treated as managed. An unrelated `/opt/foreign/agent-statusline` status line and hook were deleted on uninstall. | 0.2.1 | Resolved by matching the absolute path of this installation's console script, with positive exact-path and negative same-basename regressions for the status line and every hook slug |
| INSTALL-011 | High | Installation overwrote a `statusLine` and a checkout symlink belonging to another tool. The settings format holds one status line, so the replaced entry was unrecoverable. | 0.2.1 | Resolved by refusing before any mutation when either is not owned, keeping reinstallation of our own entry idempotent |
| INSTALL-012 | High | A non-object `hooks` container was rejected only after the checkout symlink and a backup already existed, and a non-list event container reached list processing and raised `AttributeError`. Uninstall accepted the same malformed container silently. | 0.2.1 | Resolved by validating every schema condition the operation needs before the first mutation on both paths, with full-run regressions asserting bytes, symlink, backup, and temporary-file state |
| INSTALL-013 | Medium | `--dry-run` printed "nothing will be written" but left an empty configuration directory behind, created by verification state placed under it. | 0.2.1 | Resolved with INSTALL-016 by moving verification state to a system temporary directory |
| INSTALL-014 | Medium | Expected filesystem failures during backup, temporary-file creation, publication, and symlink creation escaped as raw tracebacks. | 0.2.1 | Resolved by reporting them as concise errors that preserve the original bytes and leave no temporary file, with injected read-only, missing-directory, backup, and symlink failures |
| INSTALL-015 | High | The exact-command matcher introduced by INSTALL-007 no longer recognized the literal `~/.claude/statusline/...` commands written by the released v0.2.0 installer. Reinstalling stacked four new hooks beside three retained ones, and uninstalling left the originals behind. | 0.2.1 | Resolved by expanding a leading `~` before the anchored comparison, so legacy entries match only when they resolve to the managed directory, with upgrade and removal regressions and lookalike negatives |
| INSTALL-016 | High | Verification used the fixed path `<config>/.verify-state` and always removed it recursively, so a normal install deleted a pre-existing directory of that name and its contents. | 0.2.1 | Resolved by creating a unique system temporary directory and removing only what was created, with a regression proving pre-existing contents survive |
| INSTALL-017 | High | Confinement was checked against path strings and then acted on through those same strings. Swapping a checked directory for a symlink in that window redirected publication, overwriting an unrelated file outside the configuration directory. | 0.2.1 | Resolved by binding publication to an opened directory descriptor reached without following any symlink, with a deterministic injected-race regression |
| INSTALL-018 | High | Installation refused over a foreign `statusLine` only when a command string could be parsed out of it. A `statusLine` that was a bare string, a list, or an object without a `command` key was silently overwritten, while uninstall preserved all three — the same install/uninstall asymmetry INSTALL-011 existed to remove. | 0.2.1 | Resolved by keying the refusal on the presence of the entry rather than on a readable command, with regressions for each unreadable shape and a matching uninstall-preservation case |
| INSTALL-019 | High | `_open_publish_dir` bound every path component *below* the configuration root to a descriptor, but opened the root itself with a plain, path-named `os.open()` — no `O_NOFOLLOW`, no walk from `/`. Swapping the configuration directory for a symlink in the window between resolving it and opening it redirected publication to an outside file, exactly as INSTALL-017 did for nested components. | 0.2.1 | Resolved by walking every component of the resolved root, starting at `/`, with `O_DIRECTORY` and `O_NOFOLLOW` (`_bind_directory`), with a deterministic injected root-swap regression and a companion mutation test that restores the pre-fix root-open and shows it exploitable |
| INSTALL-020 | High | Install and uninstall are two separate mutations — a checkout symlink change and a settings rewrite — with no shared commit point. An expected failure between them left inconsistent state: a failed `os.symlink` during reinstall deleted the pre-existing managed link; a failed backup on a fresh install left a new link behind with settings untouched; a failed backup on uninstall removed the managed link while settings still referenced it. | 0.2.1 | Resolved by snapshotting the link's prior state before mutation (`_LinkGuard`) and rolling it back — restoring a pre-existing link, or removing a newly created one — whenever the paired mutation dies, with full-`run()` regressions for all three failures plus a mutation test disabling rollback |
| INSTALL-021 | Medium | `os.fchmod(fd, mode)` ran on the raw descriptor from `os.open()` before `os.fdopen()` took ownership of it. A failure there died without closing `fd`; the temporary directory entry was removed, but the descriptor stayed open for the life of the process. | 0.2.1 | Resolved by closing the descriptor explicitly if `fchmod` fails, before `os.fdopen` would otherwise take over that responsibility, with an injected-failure regression asserting both a closed descriptor and no remaining temp file |
| INSTALL-022 | Medium | Removing the last managed hook from a group dropped the whole group, including any other fields it carried. A managed `SessionEnd` group holding a user's `matcher` lost both the hook and the matcher on uninstall. | 0.2.1 | Resolved by preserving a group with `"hooks": []` when it carries fields other than `hooks`, and only dropping a group that is debris (no foreign fields, no hooks left), with reinstall and uninstall round-trip regressions |
| INSTALL-023 | High | Confinement was decided once, correctly, but each operation on the configuration directory re-derived it from `cdir`'s pathname independently. An *ordinary* directory (no symlink at all) placed at that pathname between an earlier read and a later write was followed, because `O_NOFOLLOW` refuses a symlink but not a plain rename. | 0.2.1 | Resolved by binding the configuration directory once per `run()` call and routing every read, backup, link mutation, and publish in that call through the same descriptor, with a deterministic injected directory-swap regression for both install and uninstall plus a mutation test that restores per-call rebinding and shows it exploitable |
| INSTALL-024 | High | A failure while restoring the checkout symlink after a primary failure was caught and discarded, contradicting the documented claim that an interrupted install or uninstall resolves to fully applied or fully as it was. | 0.2.1 | Resolved by having restoration report success or failure explicitly; a failure is now printed alongside the original error instead of being silently swallowed, with paired-failure regressions (both the primary operation and the restoration step fail in the same run) for both directions |
| INSTALL-025 | Medium | The initial settings read and the backup copy were made by plain pathname, outside the descriptor binding publication used, so they were not covered by the same confinement guarantee. | 0.2.1 | Resolved together with INSTALL-023: both now route through the same bound descriptor as publication |
| INSTALL-026 | High | Checkout-shape ownership accepted any interpreter whose program name started with "python" paired with the right script path, rather than the exact interpreter this installation would have written. A foreign Python paired with the expected script path was treated as managed and removed on uninstall. | 0.2.1 | Resolved by requiring the exact `sys.executable` for the current form, and the documented literal `python3` only for the v0.2.0 legacy form — never generalized to other "python*" names — with negative regressions for both the status line and every hook slug and a full-uninstall preservation regression |
| TEST-001 | Medium | The local development and release gate had no formatter, type checker, coverage measurement, or commit-time check. A green pytest run was not sufficient evidence: the first broad repository review found destructive installer behavior (INSTALL-001 through INSTALL-026) despite the suite passing throughout. | 0.2.2 | Resolved locally by [ADR 0023](adrs/0023-use-a-locked-local-quality-gate.md): a committed `uv.lock`, and a pre-commit gate running Ruff, Black, and mypy from the locked environment, plus subprocess-aware coverage measurement at release review. Hosted CI's own moving tool versions are a separate, still-open limitation, deferred to 0.2.12 |
| TEST-002 | Low | The regression for malformed transcript permission fallback used a falsy value, so it passed against the unfixed truthiness-based implementation and did not protect the correction. | 0.2.3 | Resolved by using a reachable truthy non-string transcript value that fails when the correction is removed |
| TEST-003 | Low | The persisted-ledger cleanup layer for an unsupported cached conversation root changed on-disk recovery behavior but had no regression protecting it. | 0.2.3 | Resolved by asserting an updated session is saved without the unsupported root |
| HOST-001 | Medium | Successfully decoded non-object payloads reached mapping field access and removed the complete status line for that redraw. | 0.2.3 | Resolved by the mapping boundary and minimal fallback in [ADR 0032](adrs/0032-normalize-malformed-host-input-at-the-boundary.md) |
| HOST-002 | Medium | Successfully decoded non-object transcript rows reached transcript field access instead of being skipped, preventing later valid rows from contributing. | 0.2.3 | Resolved by mapping guards in both incremental-total and conversation-root paths, with later-valid-row regressions |
| HOST-003 | Medium | Host-derived numeric fields were converted and formatted directly, so invalid, non-finite, oversized, or unusable reset-time values could raise or emit misleading `nan`/`inf` text. | 0.2.3 | Resolved by bounded finite coercion at helper, formatter, transcript, payload, and reset-time boundaries while preserving valid forms |
| HOST-004 | Medium | Unexpected nested transcript containers such as non-object message, usage, cache, hook-info, tool-input, or command-content values reached container-specific operations and could stop incremental parsing. | 0.2.3 | Resolved by narrow container guards that ignore unsupported nested values without changing valid transcript signals |
| HOST-005 | Medium | Valid JSON values of the wrong shape in path, sequence, permission-mode, or session-identifier fields reached filesystem/container operations and could remove the complete status line. | 0.2.3 | Resolved by narrow payload-field shape guards and fallback behavior, with end-to-end regressions |
| HOST-006 | High | A non-string transcript conversation identifier could poison both cached transcript state and the shared accounting ledger, then remove the status line across sessions. | 0.2.3 | Resolved by accepting and caching only non-empty string roots and tolerating unsupported roots already present in persisted state |
| HOST-007 | Medium | A non-string transcript tool name was used as a mapping key before the incremental offset advanced, so the same malformed row removed every later redraw for that session. | 0.2.3 | Resolved by assigning unsupported names to the existing unknown-tool bucket before accumulation |
| STORAGE-001 | Low | The new direct-state-name boundary still accepted the reserved components `.` and `..`, so callers could construct a root or parent path instead of one direct state filename. | 0.2.4 | Resolved by rejecting reserved components before path construction, with focused path regressions |
| STORAGE-002 | Medium | State-root creation and verification ran while module constants were imported, so a configured root that was a file or had an inaccessible parent aborted the process before the renderer's optional-state fallbacks could run. | 0.2.4 | Resolved by making package state entries lazy and verifying the root only on first filesystem use; fresh-process regressions prove rendering survives while the unusable target remains untouched |
| STORAGE-003 | Medium | Deeply nested valid JSON could raise a decoder `RecursionError` outside the JSON and JSONL malformed-state fallbacks and remove the complete status line. | 0.2.4 | Resolved by treating decoder `ValueError` and `RecursionError` as malformed state while preserving filesystem-error and unsafe-entry refusal, with real deep-input, JSONL-tail, and injected decoder regressions |
| LEDGER-001 | Medium | A malformed persisted per-session row such as a list reached mapping operations during a ledger transaction, preventing the update or close operation instead of repairing that row while preserving valid siblings and metadata. | 0.2.4 | Resolved by normalizing only mapping-shaped session rows at the transaction boundary, with save, update, close, and preservation regressions |
| TRANSCRIPT-001 | Medium | An invalid cached transcript offset was reset to zero while its prior totals were retained, so replaying the transcript counted already-observed usage and activity a second time. | 0.2.4 | Resolved by discarding cached totals whenever the offset is invalid, with negative, boolean, and container-offset regressions |
| TRANSCRIPT-002 | Medium | Transcript-cache lock, read, refusal, or publication failures propagated through both cache callers and removed the renderer output, even when a result had already been computed. | 0.2.4 | Resolved by returning the established blank/`None` fallback before the updater and the captured totals/root after it, while leaving storage refusal and prior bytes intact; permission, symlink, and post-updater regressions cover the boundary |
| TRANSCRIPT-003 | Medium | A current-schema cache row with a valid EOF offset but non-mapping totals reused the offset with blank totals, silently publishing zero without replaying the transcript. | 0.2.4 | Resolved by validating offset and totals as one unit and replaying from byte zero when either is invalid, while preserving a valid root and sibling cache rows |
| TEST-TRANSCRIPT-001 | Medium | The subprocess concurrency regression assumed its JSON result was the only stdout line, but subprocess-aware coverage can add diagnostic output, making the gate fail while parsing otherwise valid evidence. | 0.2.4 | Resolved by parsing the explicit final JSON line, matching the locked coverage environment |
| PROBE-001 | Medium | Probe-cache read or publication failures escaped the cache boundary and could remove probe-backed status information instead of returning the value computed for that redraw. | 0.2.4 | Resolved by preserving the existing computed-value fallback across storage failures, with read and publication failure regressions |
| PROBE-002 | Low | Concurrent stale callers for the same probe key could each return a different computed value even though only one became the cached value for that interval. | 0.2.4 | Resolved by returning the winner selected inside the locked transaction, with a same-key convergence regression |
| PROBE-003 | Medium | An oversized positive or negative persisted probe timestamp could raise `OverflowError` during freshness arithmetic and remove probe-backed status information. | 0.2.4 | Resolved by treating freshness arithmetic overflow as stale cache state, with both-sign regressions |
| RUNTIME-001 | High | If atomic ledger publication failed after the locked updater computed a complete aggregate, runtime fallback discarded that result and returned current-payload-only totals, omitting historical exactly accounted money from the redraw. | 0.2.4 | Resolved by retaining the computed aggregate when available while preserving prior ledger bytes, with a fail-after-updater exact-money regression |
| COST-001 | High | Rolling `24h`, `7d`, and `30d` totals assigned each recently updated session's complete lifetime cost to the window, so resuming an old session could report historical money as recent spend. | 0.2.5 | Resolved by [ADR 0022](adrs/0022-account-rolling-costs-with-timestamped-deltas.md): locked positive-delta events, non-accrual migration seeds, assistant-time attribution, independent completeness, and explicit exact lower bounds |
| COST-002 | High | A ledger storage failure before the updater ran built a current-payload-only fallback but marked every rolling window complete, presenting unknown historical spend as an exact total. | 0.2.5 | Resolved by preserving the renderable current lower bound while forcing all fallback window completeness flags false; the existing storage-failure regression now verifies amounts and markers |
| COST-003 | High | Journal-shaped fields without a recognized schema were silently replaced during migration, erasing malformed or partial evidence and allowing later windows to appear complete. | 0.2.5 | Resolved by preserving any schemaless journal artifacts unchanged and failing closed as an incomplete lower bound, while a lone row seed marker is safely reconstructed from its lifetime evidence |
| COST-004 | High | An empty host session identifier could create a lifetime row but no valid cost event, so rolling windows rendered bare exact zero despite known current spend; normalization would also risk colliding with the existing `?` fallback or duplicating a v0.2.4 row. | 0.2.5 | Resolved by preserving the packet's opaque-string identity contract and accepting empty strings in seed and ordinary events, with an in-memory transaction regression |
| COST-005 | High | Missing, malformed, negative, zero, or unrepresentably large host duration was reconstructed as an observation-time session start (or could overflow timestamp conversion), allowing an unknown first-sighting lifetime to appear exactly in-window or remove the render. | 0.2.5 | Resolved by assigning a reconstructed start only from a positive duration bounded by observation time; unusable duration remains an unattributed seed, with host-boundary and fixed-clock regressions |
| COST-006 | High | Python 3.9 and 3.10 reject the host's trailing-`Z` UTC assistant timestamps in `datetime.fromisoformat`, silently falling back to observation time instead of using the preferred attribution evidence. | 0.2.5 | Resolved by normalizing only a trailing `Z` to `+00:00` before parsing, matching the transcript parser and preserving behavior on newer interpreters |
| COST-007 | High | Fractional observation clocks were compared with whole-second serialized events, so an event recorded at the exact inclusive cutoff could be excluded by the discarded fraction while the window still appeared complete. | 0.2.5 | Resolved by normalizing journal observation and cutoff arithmetic to the ledger's documented whole-second precision, with a fractional-clock boundary regression |
| COST-008 | High | A structurally valid event observed before `cost_tracking_started` was accepted as complete journal evidence and could be pruned later despite the inconsistent chronology. | 0.2.5 | Resolved by requiring every event observation to be at or after the valid tracking start for completeness and pruning; inconsistent evidence remains stored and every window stays a lower bound |
| ARTIFACT-001 | High | Unanchored source-distribution include patterns matched ignored `.pvt/docs` and `.worktrees/*/{src,tests,docs}` paths in a development checkout, allowing private Relay records and unrelated worktree content into a locally built sdist. | 0.2.5 | Resolved by root-anchored sdist paths plus a stdlib archive verifier exercised by regressions and required in both CI and Release before upload or publication |
| STATE-003 | High | Concurrent sessions shared one process-probe cache row, allowing every session inside the TTL to display the first session's PID, process count, and RSS. | 0.2.6 | Resolved by [ADR 0024](adrs/0024-scope-process-probes-by-session.md), disjoint session/parent key namespaces, and distinct-session regressions |
| STATE-004 | Medium | Path- and session-qualified probe rows accumulated without an age or entry-count lifecycle bound. | 0.2.7 | Resolved by seven-day expiry, a 256-row cap, active-row preservation, and exact-boundary regressions |
| STATE-005 | Medium | Transcript cache rows and diagnostic rate-limit observations grew for the lifetime of the installation. | 0.2.7 | Resolved by [ADR 0025](adrs/0025-bound-ephemeral-observation-state.md), transcript age/count limits, hourly touches, atomic byte-bound history compaction, and hot-path regressions |
| GOV-001 | Medium | Project authority, current continuation state, research, and the one-owner/one-reviewer boundary were available only through machine-local or historical records. | 0.2.8 | Resolved by tracked `AGENTS.md`, `HANDOFF.md`, `RESEARCH.md`, and [ADR 0026](adrs/0026-coordinate-one-owner-and-one-reviewer.md) |
| GOV-002 | Medium | Relative documentation links, ADR index coverage, release-record version agreement, serial review language, and governance privacy could drift without a deterministic gate. | 0.2.8 | Resolved by the repository documentation verifier and synthetic pass/failure regressions |
| TERM-001 | Medium | Printable width used code-point count rather than terminal-cell width, so wide characters could exceed the physical line limit while combining marks consumed false budget. | 0.2.9 | Resolved by [ADR 0027](adrs/0027-measure-cells-and-sanitize-terminal-output.md), cell-aware measurement, and wide/combining width regressions |
| TERM-002 | Medium | Host and user-controlled row inputs could emit line, format, bidirectional, arbitrary SGR, or terminal-command controls. | 0.2.9 | Resolved by exact package-SGR allowlisting and control/escape sanitization before fitting, with injection and malformed-sequence regressions |
| TERM-003 | Medium | Nested Git branch discovery rebound the working directory used by the later `SYSTEM` disk probe, so its free-space evidence could describe a child repository rather than the current workspace. | 0.2.9 | Resolved by keeping display-only Git discovery separate from the original workspace path, with a disk-key regression |
| TERM-004 | Low | Fractional allowance usage was rounded for display, so 99.5 could appear as 100% before the numeric overage boundary was reached. | 0.2.9 | Resolved by flooring only the displayed 5h/7d allowance value while retaining burn-rate precision and numeric `pct >= 100` overage behavior |
| TEST-004 | Low | The first Unicode-width assertion combined one wide character with one combining mark, allowing the two opposite errors in naive code-point counting to cancel to the expected total. | 0.2.9 | Resolved by asserting wide and combining widths independently before the combined example; the naive-width mutation now fails |
| TEST-005 | Medium | The installed-shape smoke rendered only an empty object, proving entry-point startup without exercising any approved row or transcript-backed evidence from the wheel users install. | 0.2.10 | Resolved by building once, installing that wheel without dependencies, and applying the shared exact-row and transcript-evidence verifier from an unrelated working directory |
| TEST-006 | Medium | Source renderer tests used a nonexistent transcript, fixed `/tmp` project paths, and far-future reset clocks, so they neither exercised transcript parsing nor proved independence from host paths and time. | 0.2.10 | Resolved by shared privacy-neutral templates whose paths and assistant/reset clocks are materialized inside each caller's disposable workspace |
| TEST-007 | Low | The floored-percentage regression searched the complete usage row, so a legitimate fractional burn-rate value equal to the input percentage could falsely fail the display-only assertion. | 0.2.10 | Resolved by constraining the assertion to the allowance segment before the separately precise burn-rate field |
| TEST-008 | Medium | There was no installed health check that could exercise the complete renderer without replaying a real payload against live configuration and accounting state. | 0.2.11 | Resolved by an installed self-test derived from `ORDER` and equivalent to the v0.2.10 synthetic contract, with fresh private home/config/state/cwd and child-output suppression |
| DIAG-001 | Medium | Unexpected renderer exceptions were hidden by the host without leaving any privacy-safe local evidence for diagnosis. | 0.2.11 | Resolved by a private atomic breadcrumb allowlisting only schema, UTC time, fixed phase, and exception type while preserving the original error and excluding malformed input and broken pipes |
| PUB-001 | High | Removing the root `/.claude/` ignore while adopting other private workspace directories allowed assistant-native account, spend, session, or prompt state to re-enter a future public commit. | 0.2.12 | Resolved by permanently tracking all three root boundaries—`/.claude/`, `/.pvt/`, and `/.worktrees/`—and enforcing them in the public-readiness policy |
| PUB-002 | High | CI and Release executed third-party actions through mutable major-version tags, allowing upstream tag movement to change trusted workflow code without a repository change. | 0.2.12 | Resolved by reviewed full-SHA pins with readable version comments plus a deterministic policy that rejects moving or abbreviated refs |
| PUB-003 | Medium | ADR 0018 included exact shared private-account allowance, timing, and consumption measurements that were unnecessary to preserve the lean-CI decision. | 0.2.12 | Resolved by public-safe ADR 0033, the ADR 0034 ordinary-ref rewrite, and replacement source archives for every existing affected Release |
| PUB-004 | High | The proposed public switch had neither hosted evidence for the lean workflows nor an enforceable boundary separating visibility from post-conversion `main` protection. | 0.2.12 | Active patch-train workflows and [the tracked readiness audit](PUBLIC_READINESS.md) make visibility an explicit authorization and require API-verified no-bypass protection before declaring the public baseline complete |
| PUB-005 | High | Reachable branches and v0.2.1 through v0.2.11 tags retained the private ADR blob, while 12 release-spine merge commits retained a personal maintainer author identity. | 0.2.12 | Resolved for all ordinary branch and tag refs by the atomic ADR 0034 rewrite and fresh remote audit; twelve provider-managed historical pull heads remain as the explicitly accepted ADR 0035 residue |
| PUB-006 | High | The release process verified candidate content and tree identity but did not verify the author, committer, and annotated-tagger metadata generated at the merge and tag boundaries. | 0.2.12 | Resolved prospectively by GitHub and local no-reply controls plus automatic `main` commit and Release tag identity gates; historical closure remains PUB-005 |
| PUB-007 | High | CI path filters skipped documentation-only pull requests and `main` pushes, and no hosted step audited the complete candidate ancestry, allowing an old unsafe commit to return under a new ref without exercising the public-readiness gate. | 0.2.12 | Resolved by an always-on complete-ancestry audit for every pull request and `main` push, a release ancestry audit, and policy regressions that forbid path-filter bypass while preserving a minimal documentation-only job |
| PUB-008 | High | Artifact and reachable-history privacy scanners silently skipped a regular member or blob above two MiB, allowing oversized private evidence to pass both policies. | 0.2.13 | Resolved by ADR 0036 fail-closed rejection on both paths, synthetic oversized regressions, a strict ordinary-history rescan, and the complete retained Actions exposure inventory |
| PUB-009 | High | Requiring only CI's always-on `checks` job would allow a code pull request to merge even when one or more Python matrix jobs failed. | 0.2.13 | Resolved by one stable aggregate `required` job that fails unless policy checks pass and the matrix either passes for full scope or is deliberately skipped for documentation-only scope; active no-bypass ruleset `22966865` requires that GitHub Actions result |
| CI-GATE-001 | High | The aggregate `required` job treated every scope result other than literal `true` as documentation-only, so a missing or malformed output could skip the full gate while branch protection passed; the policy verifier also accepted making its enforcement step conditional or non-blocking. | 0.2.13 | Resolved by accepting only explicit `true` and `false`, failing every other scope value, requiring both scope outputs, forbidding step-level `if` and `continue-on-error` on enforcement, and exercising the actual shell plus all four policy mutations |
| CI-GATE-002 | High | The aggregate policy accepted a false extension of the job's `always()` condition, a shell override that disabled inherited fail-fast behavior, and quoted, whitespace-varied, or escaped YAML spellings of protected keys, allowing required failures to be skipped or masked. | 0.2.13 | Resolved by requiring the exact job condition, making the script self-contained with `set -eu`, permitting only the reviewed canonical direct keys on the job and enforcement step, and exercising failures without inherited shell flags |
| CI-PUBLIC-001 | Medium | After public conversion, hosted macOS remained manual and current guidance still described private-repository billing, leaving full-scope changes without automatic evidence for the supported platform-specific memory probe. | 0.2.14 | Resolved by one automatic Python 3.12 macOS lane for full scope, including its result in the stable aggregate gate, preserving the documentation-only boundary, and replacing stale current guidance with ADR 0038 |
| RELEASE-001 | Medium | The completed hardening train lacked an explicit supported baseline, while the retained historical integration branch still carried the old proposed v0.3.0 name and could be mistaken for a merge candidate. | 0.3.0 | Resolved by [ADR 0039](adrs/0039-declare-the-production-ready-public-baseline.md), explicit source-only treatment of the historical branch, the production maturity classifier, and exact milestone release evidence |
| RELEASE-002 | Medium | The updating guide told exact Git-tag installations to run `uv tool upgrade agent-statusline`, which reports nothing to upgrade and leaves the old tag installed. | 0.3.0 | Resolved by requiring an explicit `uv tool install --force` from the newer immutable tag and rerunning managed wiring, while retaining `git pull` only for development checkouts |
| PERF-001 | Medium | A fresh renderer process imported CLI-only `argparse`, cold-probe `subprocess`, and `shutil` through width and temporary-file helpers, consuming avoidable work on every redraw. | 0.3.1 | Resolved by [ADR 0040](adrs/0040-remove-avoidable-hot-path-imports.md): lazy cold-path imports, direct equivalent width and private temporary primitives, a deterministic import budget, and non-gating isolated benchmark evidence |
| RECORD-006 | Low | The first aggregate owner record reported 85.22% full-suite coverage from an existing cumulative coverage database rather than the reproducible clean exact-target result of 83.23%. | 0.2.4 | Resolved by withdrawing 85.22%, recording the rejected target's clean 83.23% result, and running the correction suite with a fresh external coverage database |
| RECORD-007 | Low | The corrected aggregate owner record narrowed clean subprocess-aware coverage to 85.34%-85.44%, but independent runs across supported interpreters and clean checkout shapes produced measurements outside that range. | 0.2.4 | Resolved by removing the unsupported range and retaining only the reproducible fact that the complete 390-test suite passes the enforced 77.0% coverage threshold; individual measurements remain environment-specific evidence |

## v0.2.4 reviewed release record

The accepted implementation boundary is the released v0.2.3 commit
`0375e6b2c6a5fc473c0ff335f76df30b5cdb7bcb` followed by these independently
reviewed exact component heads:

| Component | Accepted exact SHA | Evidence at acceptance |
| --- | --- | --- |
| Storage foundation | `8f67f12663d5d0c8ac265a901a27d98188c8e78f` | 28 focused tests and the locked all-files gate |
| Ledger adapter | `e20b3af60c0a959e4b8d0c448c68bfb139ddae92` | 47 ledger/storage tests and the locked all-files gate |
| Transcript adapter | `106281f4f242807f297d0e9ebcdd7b28e93e8671` | 38 focused tests, 355 full tests at 82.65% subprocess-aware coverage, and the locked all-files gate |
| Probe adapter | `9704b5ba1ad65c0056cb1639b63b26f320a9bcbc` | 38 probe/storage tests and the locked all-files gate |
| Runtime wiring | `1d4ec4777af41d1f8f596f9f2cd82df5c1d293f2` | 121 focused tests, 50/50 repeated concurrency invocations, 380 full tests at 84.70% subprocess-aware coverage, and the locked all-files gate |
| Release records | `06a34c407c264881d3d052f84484bba79a371b20` | Renewed exact-SHA acceptance with no findings after RECORD-005 restored the accepted transcript-finding severity; the locked all-files gate and 380 full tests at 84.70% subprocess-aware coverage |

The dependency-correct Wave 2 aggregate is
`092540c8022258dc479fffd0291bd0e020d16e8b`; its accepted inputs were integrated
without conflict repair and were byte-identical to their reviewed heads. The
superseded review targets were `40cc6a81ea4250560c296c0b9af190d252033a00`,
`ae0965a2cd1b95d89abc31a34b8e03a0a5e7dada`,
`1d4c05b6f4ab2d982c370cfd8ebc72327b3a14f2`,
`f2683f5de8eeacd1ae86c339eb9a88d5259c16f3`, and
`439bf4cdb8f2dc240c96837db3989a4e57c59285`; each was corrected and replaced.
Target `f99fad9ce8d313422ffff6f58d4a9212728ab37b` was invalidated when its review
corrections changed the head.

Codex assembled first aggregate RC
`de2fb47a1420bf27429f49d4d42ac5697db73772` directly from the accepted
release-records head, with no further component integration or conflict repair.
Independent exact-SHA review rejected it for STORAGE-002, STORAGE-003,
TRANSCRIPT-002, TRANSCRIPT-003, and RECORD-006. Its clean full-suite result is
380 tests at 83.23% subprocess-aware coverage; the prior 85.22% claim matched
an existing cumulative database and is withdrawn.

The bounded owner correction changes only the affected storage, path, and
transcript boundaries, their regressions, and current v0.2.4 records. On
macOS/Python 3.11.5 it passed the locked all-files checks, 179 focused
storage/ledger/transcript/probe/runtime tests, 80/80 repeated concurrency/dedup
invocations, and 390 full tests above the required 77.0% subprocess-aware
coverage gate from clean committed worktrees using fresh external coverage
databases. Both source and wheel builds passed. A fresh Python 3.9.6 environment
installed the correction wheel with no index and no dependencies, reported no
runtime `Requires-Dist`, and passed synthetic render, hook, ledger,
installed-shape, checkout-shape, and uninstall smokes.

Independent exact-SHA review of correction
`f94b59a204f1137608a13ec4dcd5c4c9b1082e80` closed STORAGE-002, STORAGE-003,
TRANSCRIPT-002, and TRANSCRIPT-003, and rejected only RECORD-007. Reviewer
measurements were 83.37% on Python 3.9.6, 83.47% twice on Python 3.11.5, and
84.92% in a separate clean detached Python 3.11.5 checkout. Those point
measurements are retained as environment-specific evidence, not a universal
percentage or range; the reproducible release claim is that all 390 tests pass
the enforced 77.0% coverage threshold. This records-only owner correction
changes no runtime, test, workflow, configuration, or release mechanics.

Final independent review accepted exact corrected head
`f7952f046bebc2dca703478ca954093dbcc08ec2`, which merged through PR #4 at
`04120ec52adb325462bbf3df50fcde4a662f0aff`. PR #5 then merged the separately
reviewed workflow assertion correction at exact release commit
`73643bb9fe5b846202d3311f7a0f4a1bf6b3af87`. Hosted CI run 34555947827 passed
that exact main commit on Python 3.9 through 3.13, with macOS deliberately
skipped. Annotated tag `v0.2.4`, Release run 34556042333, the GitHub Release,
and downloaded wheel/sdist digests all agree with that commit; the downloaded
wheel passed an isolated installed lifecycle and has no runtime dependencies.

The read-before-confinement advisory recorded in an earlier round of this table
is substantially closed by INSTALL-023/025: the initial settings read now goes
through the same bound descriptor as the eventual write, not merely reordered
ahead of it. A deliberate same-user pathname race manipulating filesystem
objects between two of this installer's own operations -- of which this was
one instance -- is outside the practical local threat model this project
targets ([ADR 0031](adrs/0031-practical-local-threat-model.md)) and is not
carried here as an open release-blocking defect.

A numbering note for readers of the review channel: informal correspondence
external to this table referred to the four findings above as "INSTALL-018"
through "INSTALL-022," reusing IDs already assigned in this table to the
resolved `statusLine`-shape finding. That external "INSTALL-020" (malformed or
unknown `statusLine` values being overwritten) describes exactly the defect this
table already records as INSTALL-018, resolved before this round began;
reproduction against the current branch tip confirmed all five named shapes
(`"foreign-string"`, `[]`, `{"type": "command"}`, `{"type": "text", "text":
"hello"}`, `{"command": null}`) are already refused, and two of those exact
shapes were added to the existing regression as additional coverage. It is not
a new row. The four genuinely new findings keep the next sequential IDs in this
table, INSTALL-019 through INSTALL-022, matching the identifiers already used
for them in the tracked review channel before this session started.

INSTALL-005 through INSTALL-009 were found while reviewing and adversarially
testing the extracted commits, not in the original implementation. Each is fixed
here because each is the same ownership or fail-closed property this release
exists to guarantee.

INSTALL-007 and INSTALL-008 were surfaced by an independent adversarial review of
this branch. INSTALL-007 is the more serious of the two: it had been recorded as
resolved by INSTALL-003 when only part of it was, and an unanchored suffix match
would have deleted an unrelated tool's status line and hooks on uninstall.

INSTALL-010 through INSTALL-017 came from a second independent review of the
corrected branch. Three of them are defects introduced by earlier fixes on this
same branch rather than by the original implementation: INSTALL-015 is fallout
from the exact-command matcher added for INSTALL-007, and INSTALL-013 and
INSTALL-016 are properties of verification that the ownership work never
examined. INSTALL-017 is the residue of INSTALL-008 -- refusing an out-of-tree
path closed the obvious hole and left the window between checking a path and
writing to it.

INSTALL-018 was found by self-review after INSTALL-010..017 were pushed, and it
is the clearest instance of the pattern below: INSTALL-011 added a refusal and
phrased it in terms of a *command*, when the thing being protected is the
*entry*. Every shape the matcher could not read fell through the guard that was
written to protect it.

The pattern worth naming: each round of ownership fixes narrowed *what* is
claimed without asking what else the installer touches. Ownership matching,
refusal ordering, verification state, and publication mechanics are four separate
surfaces, and fixing one repeatedly left the others stating guarantees the code
did not keep.

INSTALL-019 through INSTALL-022 came from a third independent review, of the
branch tip carrying INSTALL-018. Two are the same "protect the descriptor, not
just the path" lesson as INSTALL-017 applied one level up (INSTALL-019, the
confinement root) and applied to the write path's own descriptor lifecycle
(INSTALL-021). The other two are about the release's actual promise rather than
about symlink confinement: an install or uninstall that fails partway must not
leave the checkout link and settings disagreeing about what is installed
(INSTALL-020), and ownership of a hook entry must not reach into fields on its
containing group that the release never claimed (INSTALL-022).

INSTALL-023 through INSTALL-026 and RECORD-001 came from a fourth independent
review, of the branch tip carrying INSTALL-019..022. INSTALL-023 is the
deepest instance yet of the "protect the descriptor, not just the path"
lesson: binding the root correctly at one point in the code does nothing if a
later point re-derives it independently, and INSTALL-025 was a direct
consequence -- the read and the backup were exactly such independent
re-derivations. INSTALL-024 is a different kind of gap: the mechanism was
already in place, but its own failure path silently discarded evidence that it
had not done its job. INSTALL-026 is the same unanchored-ownership pattern as
INSTALL-007 and INSTALL-010, recurring a third time at the one remaining
un-anchored token: the interpreter naming the script this installer wrote.
RECORD-001 is process, not code: two regressions in this table's own test
suite carried finding IDs one number stale, correctly identifying the class of
defect each protects against but not the ID that class was ultimately given.
