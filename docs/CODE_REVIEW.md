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

The read-before-confinement advisory recorded in an earlier round of this table
is substantially closed by INSTALL-023/025: the initial settings read now goes
through the same bound descriptor as the eventual write, not merely reordered
ahead of it. What remains open, newly observed while verifying INSTALL-023 and
not part of Codex's reported findings: when `settings.json` is a symlink into a
*subdirectory* of the configuration directory (rather than sitting directly in
it), the intermediate subdirectory is still walked fresh from the bound root
descriptor on each of the read, backup, and write calls, rather than that walk
also being bound once and reused. An ordinary-directory swap of that
intermediate subdirectory between two of those calls redirects the later one,
the same class of gap INSTALL-023 closed for the configuration root itself,
one level deeper and narrower in practice (it requires a nested symlinked
`settings.json`, not the common direct case). Reproduced by execution against
this branch; not fixed here, and not assigned an ID by this table's author --
left for independent review to confirm and number, per this project's
owner/reviewer protocol, rather than expanding this round's scope
unilaterally.

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

## Verification log

Executed evidence for each pushed SHA on `claude/fix/v0.2.1-install-ownership`,
scoped to counts and pass/fail outcomes plus named open items -- reproduction
transcripts, injection mechanics, and cross-assistant process narration stay in
the private review channel (`.pvt/`, ignored by Git; see its `README.md` for
the boundary and why). This section exists so a reviewer with only the pushed
branch -- no access to that private channel -- can still see what was run, at
which SHA, and what is still open, rather than having to take the commit
message's word for it.

### `47a60bc` / `7f70a3b` -- INSTALL-010..018

- 186 tests passed (from 137); `ruff check src tests install.py` clean;
  `git diff --check` clean.
- 11/11 mutation battery killed (`47a60bc`) plus one further mutation for the
  INSTALL-018 correction (`7f70a3b`).
- Both artifacts built from a clean tree; a fresh Python 3.9.6 venv installed
  the exact wheel (`0.2.1.dev15+g7f70a3ba4`); both install shapes proven end
  to end against disposable `HOME`/`CLAUDE_CONFIG_DIR`/`AGENT_STATUSLINE_STATE`.
- Hosted workflows, tags, and PRs confirmed unchanged.
- Open at this SHA, addressed in the next entry: INSTALL-019 through
  INSTALL-022.

### `d57c96e` / `91ebced` -- INSTALL-019..022

- 200 tests passed (from 186); ruff clean; `git diff --check` clean.
- 5/5 targeted mutations killed (one per fix, plus the read-before-confinement
  advisory).
- Both artifacts built from a clean tree; a fresh Python 3.9.6 venv installed
  the exact wheel (`0.2.1.dev17+g91ebcedf2`); both install shapes proven end to
  end, including the installed-wheel INSTALL-022 case specifically.
- Hosted workflows, tags, and PRs confirmed unchanged.
- Open at this SHA, addressed in the next entry: INSTALL-023 through
  INSTALL-026, RECORD-001.

### `e8bf627` (code) / this commit (records) -- INSTALL-023..026, RECORD-001

- 213 tests passed (from 200); `ruff check src tests install.py` clean;
  `git diff --check` clean.
- 3 targeted mutation experiments, 11 of 12 regressions confirmed load-bearing
  (the twelfth is a positive-control test unaffected by design, not a miss):
  reverting the `cdir_fd` reuse `_open_publish_dir` now accepts fails both
  INSTALL-023/025 directory-swap regressions; reverting `_LinkGuard.rollback`
  to discard a secondary failure fails both INSTALL-024 paired-failure
  regressions; reverting the checkout interpreter check to
  basename-starts-with-"python" fails 7 of 8 INSTALL-026 regressions.
- Both artifacts built from a clean tree; a fresh Python 3.9.6 venv installed
  the exact wheel at the branch tip; both install shapes proven end to end
  against disposable `HOME`/`CLAUDE_CONFIG_DIR`/`AGENT_STATUSLINE_STATE`,
  including a deterministic ordinary-directory-swap reproduction against the
  real installed console script for INSTALL-023.
- Hosted workflows, tags, and PRs confirmed unchanged; `.worktrees/codex`
  untouched; the primary clone stayed on clean `main`.
- Open at this SHA:
  - The nested-subdirectory nested-symlink gap described above, under
    INSTALL-026's table row -- reported here, not yet independently reviewed
    or assigned an ID.
  - **Request to the reviewer:** whether the read-before-confinement TOCTOU
    that an earlier round left open is now fully closed by INSTALL-023/025, or
    whether a narrower window remains worth demonstrating -- see the
    corresponding paragraph in
    [ADR 0020](adrs/0020-own-only-managed-configuration.md#consequences) and
    `.pvt/handoffs/CLAUDE_TO_CODEX-REVIEWS.md` for the full reasoning.
