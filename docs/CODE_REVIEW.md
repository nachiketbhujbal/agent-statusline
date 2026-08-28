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

INSTALL-005 through INSTALL-009 were found while reviewing and adversarially
testing the extracted commits, not in the original implementation. Each is fixed
here because each is the same ownership or fail-closed property this release
exists to guarantee.

INSTALL-007 and INSTALL-008 were surfaced by an independent adversarial review of
this branch. INSTALL-007 is the more serious of the two: it had been recorded as
resolved by INSTALL-003 when only part of it was, and an unanchored suffix match
would have deleted an unrelated tool's status line and hooks on uninstall.
