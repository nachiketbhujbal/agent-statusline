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
